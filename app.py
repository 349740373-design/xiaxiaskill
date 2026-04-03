import streamlit as st
import requests
from openai import OpenAI

# ================= 1. 核心配置区 =================
NOTION_TOKEN = "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"
DATABASE_ID = "3367896f77be8011b3bfdb0fa327276e"

# 从云端保险箱读取密钥，极其安全
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# 初始化引擎
client = OpenAI(api_key=OPENAI_API_KEY)

# ================= 2. Notion 交互逻辑 =================
def get_clay_intuition_data():
    """读取你的历史直觉残骸"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        return []

    data = response.json()
    slices = []
    for row in data.get("results", []):
        props = row.get("properties", {})
        scene = props.get("[场景背景]", {}).get("title", [{}])[0].get("plain_text", "") if props.get("[场景背景]", {}).get("title") else ""
        intuition = props.get("[直觉快照]", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("[直觉快照]", {}).get("rich_text") else ""
        variables = props.get("[外部变量/数据]", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("[外部变量/数据]", {}).get("rich_text") else ""
        action = props.get("[最终动作]", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("[最终动作]", {}).get("rich_text") else ""
        
        if scene:
            slices.append({"scene": scene, "intuition": intuition, "variables": variables, "action": action})
    return slices

def save_to_notion(problem, answer):
    """将认可的决策写回 Notion，形成飞轮"""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # 按照你 Notion 表格的字段格式进行打包
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "[场景背景]": {
                "title": [{"text": {"content": f"网友提问：{problem[:20]}..."}}] # 取前20个字作为标题
            },
            "[外部变量/数据]": {
                "rich_text": [{"text": {"content": f"完整问题：{problem}"}}]
            },
            "[直觉快照]": {
                "rich_text": [{"text": {"content": answer}}]
            },
            "[最终动作]": {
                "rich_text": [{"text": {"content": "夏夏已认可并沉淀该决策。"}}]
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

def ask_xiaoxia(problem):
    """大脑推演逻辑"""
    slices = get_clay_intuition_data()
    history_str = ""
    for s in slices:
        history_str += f"\n- 场景: {s['scene']}\n  外部变量: {s['variables']}\n  你的直觉: {s['intuition']}\n  最终决策: {s['action']}\n"

    system_instruction = f"""
    你现在是夏夏的数字分身 Skill。你拥有她的产品运营嗅觉、实体店实操痛感、以及对 K-pop 饭圈的敏锐度。
    你的行文风格：极其克制、冷峻、不堆砌形容词。禁止使用“宝贝”、“亲爱的”等油腻称呼。绝不在回复结尾提供任何形式的选择题或反问。
    
    你的决策逻辑参考以下真实的决策残骸：
    {history_str}
    
    当前新问题：{problem}
    请基于上述逻辑，给出最符合夏夏风格的判断。如果涉及风险，优先考虑止损；如果涉及产品，优先考虑核心交互体验。
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[
            {"role": "system", "content": "你是一个基于用户历史决策数据进行推演的数字分身。"},
            {"role": "user", "content": system_instruction}
        ],
        temperature=0.7 
    )
    return response.choices[0].message.content

# ================= 3. 网页交互界面 (UI) =================
st.set_page_config(page_title="夏夏 Skill | 运营决策大脑", page_icon="🧠")

st.title("🧠 夏夏 Skill (进化版)")
st.markdown("输入业务困局获取直觉切断。认可的建议将自动沉淀至 Notion 数据库。")

# 使用 session_state 记住生成的结果，避免一点击按钮页面刷新就弄丢了数据
if "current_problem" not in st.session_state:
    st.session_state.current_problem = ""
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "is_saved" not in st.session_state:
    st.session_state.is_saved = False

user_input = st.text_area("你的业务困局是什么？", placeholder="输入困局...", value=st.session_state.current_problem)

# 点击生成决策
if st.button("获取决策"):
    if not user_input.strip():
        st.warning("输入点什么。")
    else:
        with st.spinner("检索底层逻辑中..."):
            try:
                answer = ask_xiaoxia(user_input)
                # 把状态存起来
                st.session_state.current_problem = user_input
                st.session_state.current_answer = answer
                st.session_state.is_saved = False # 重置保存状态
            except Exception as e:
                st.error(f"引擎点火失败：{e}")

# 如果已经生成了回答，就显示出来，并给出两个反馈按钮
if st.session_state.current_answer:
    st.info("决策已生成：")
    st.write(st.session_state.current_answer)
    
    st.markdown("---")
    
    # 将两个按钮并排显示
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.is_saved:
            if st.button("✅ 极其准确，沉淀入库"):
                with st.spinner("正在写入 Notion..."):
                    success = save_to_notion(st.session_state.current_problem, st.session_state.current_answer)
                    if success:
                        st.success("已成功写入你的 Notion 数据库！数据飞轮转动+1。")
                        st.session_state.is_saved = True # 标记为已保存，防止重复点击
                    else:
                        st.error("写入失败，请检查 Notion 权限。")
        else:
            st.success("已沉淀！")
            
    with col2:
        if st.button("❌ 感觉不对，扔掉重来"):
            # 清空缓存数据，让用户重新输入
            st.session_state.current_problem = ""
            st.session_state.current_answer = ""
            st.rerun() # 强制刷新页面

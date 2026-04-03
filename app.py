import streamlit as st
import requests
from openai import OpenAI

# ================= 1. 核心配置区 =================
NOTION_TOKEN = "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"
DATABASE_ID = "3367896f77be8011b3bfdb0fa327276e"

# 从 Streamlit 后台 Secrets 读取安全密钥
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# 使用你提供的供应商专用网关地址
client = OpenAI(
    api_key=OPENAI_API_KEY, 
    base_url="http://1.95.142.151:3000/v1"
)

# ================= 2. 逻辑函数逻辑 =================
def get_clay_intuition_data():
    """从 Notion 抓取夏夏的历史决策残骸"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
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
    except:
        pass
    return []

def save_to_notion(problem, answer):
    """飞轮效应：将认可的决策写回 Notion"""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "[场景背景]": {"title": [{"text": {"content": f"沉淀：{problem[:20]}..."}}]},
            "[外部变量/数据]": {"rich_text": [{"text": {"content": f"问题：{problem}"}}]},
            "[直觉快照]": {"rich_text": [{"text": {"content": answer}}]},
            "[最终动作]": {"rich_text": [{"text": {"content": "夏夏已认可并入库。"}}] }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

def ask_xiaoxia(problem, model_name):
    """调用选定的模型进行风格化推演"""
    slices = get_clay_intuition_data()
    history_str = ""
    for s in slices:
        history_str += f"\n- 场景: {s['scene']}\n  外部变量: {s['variables']}\n  你的直觉: {s['intuition']}\n  最终决策: {s['action']}\n"

    system_instruction = f"""
    你现在是夏夏的数字分身 Skill。你拥有她的产品运营嗅觉、实体店实操痛感、以及对 K-pop 饭圈的敏锐度。
    你的行文风格：极其克制、冷峻、不堆砌形容词。禁止使用“宝贝”、“亲爱的”等油腻称呼。
    
    你的决策逻辑参考以下真实的决策残骸：
    {history_str}
    
    当前新问题：{problem}
    请基于上述逻辑，给出最符合夏夏风格的判断。
    """
    
    response = client.chat.completions.create(
        model=model_name, 
        messages=[
            {"role": "system", "content": "你是一个基于用户历史决策数据进行推演的数字分身。"},
            {"role": "user", "content": system_instruction}
        ],
        temperature=0.7 
    )
    return response.choices[0].message.content

# ================= 3. Streamlit 网页布局 =================
st.set_page_config(page_title="夏夏 Skill | 决策大脑", page_icon="🧠")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 引擎配置")
    # 这里根据你的要求改成了默认 claude-sonnet-4-6
    selected_model = st.text_input("当前模型名称", value="claude-sonnet-4-6")
    st.caption("如需更换模型，可在此直接修改。")

st.title("🧠 夏夏 Skill (Alpha)")
st.markdown("输入业务困局，获取夏夏风格的直觉切断。")

# 状态保持
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "last_problem" not in st.session_state:
    st.session_state.last_problem = ""
if "saved" not in st.session_state:
    st.session_state.saved = False

user_input = st.text_area("你的业务困局是什么？", placeholder="在此输入问题...")

if st.button("获取决策"):
    if user_input.strip():
        with st.spinner(f"正在调动 {selected_model} 提取直觉..."):
            try:
                answer = ask_xiaoxia(user_input, selected_model)
                st.session_state.current_answer = answer
                st.session_state.last_problem = user_input
                st.session_state.saved = False
            except Exception as e:
                st.error(f"接口连接失败，请确认模型名称是否正确：{e}")
    else:
        st.warning("请输入内容。")

# 结果显示与反馈
if st.session_state.current_answer:
    st.info("夏夏的建议：")
    st.write(st.session_state.current_answer)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.saved:
            if st.button("✅ 认可并沉淀"):
                if save_to_notion(st.session_state.last_problem, st.session_state.current_answer):
                    st.success("已成功同步至 Notion！")
                    st.session_state.saved = True
        else:
            st.success("已沉淀入库")
            
    with col2:
        if st.button("❌ 扔掉"):
            st.session_state.current_answer = ""
            st.rerun()

import streamlit as st
import requests
from openai import OpenAI

# ================= 1. 核心配置区 =================
NOTION_TOKEN = "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"
DATABASE_ID = "3367896f77be8011b3bfdb0fa327276e"

# 你的第三方 API 密钥
OPENAI_API_KEY = "sk-LNtZCN7ktLe1J5R7EgesEcccbD0rnO5rXp7hYBzOUXdTN9vN"
# 你的第三方 API 地址（如果你购买的服务商提供了专属链接，请把下面引号里的网址替换掉）
API_BASE_URL = "https://api.openai.com/v1" 

# ================= 2. 引擎初始化 =================
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=API_BASE_URL
)

# ================= 3. 数据抓取逻辑 =================
@st.cache_data(ttl=3600)
def get_clay_intuition_data():
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

# ================= 4. 大脑推演逻辑 =================
def ask_xiaoxia(problem):
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

# ================= 5. 网页交互界面 (UI) =================
st.set_page_config(page_title="夏夏 Skill | 运营决策大脑", page_icon="??")

st.title("?? 夏夏 Skill (Alpha 版)")
st.markdown("输入你现在面临的产品或运营纠结，获取夏夏风格的**直觉切断**。")

user_input = st.text_area("你的业务困局是什么？", placeholder="例如：合作方要求我们在周边上加印他们的 Logo，但我直觉这会破坏饭圈的购买欲，怎么选？")

if st.button("获取决策"):
    if not user_input.strip():
        st.warning("输入点什么。")
    else:
        with st.spinner("检索底层逻辑中..."):
            try:
                answer = ask_xiaoxia(user_input)
                st.success("决策已生成：")
                st.write(answer)
            except Exception as e:
                st.error(f"引擎点火失败，请检查第三方 API 的地址和余额：{e}")
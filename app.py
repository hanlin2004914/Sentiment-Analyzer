import os
import random
import asyncio
import httpx
from datasets import load_dataset
import gradio as gr

# ========== 配置 ==========
HF_TOKEN = os.getenv("HF_TOKEN")
DATASET_NAME = "jxczvlewrwuonidou/sentiment_question_set"

CATEGORY_FILES = {
    "equity_news": {
        "file": "equity_news_sentiment.json",
        "description": "公司新闻情感（影响投资者信心）"
    },
    "country_news": {
        "file": "country_news_sentiment.json",
        "description": "国家新闻情感（影响经济增长预期）"
    },
    "equity_social_media": {
        "file": "equity_social_media_sentiment.json",
        "description": "社交媒体情感（对公司）"
    },
    "equity_transcript": {
        "file": "equity_transcript_sentiment.json",
        "description": "发布会/会议转录文本情感"
    },
    "es_news": {
        "file": "es_news_sentiment.json",
        "description": "环境与社会政策新闻情感（ESG）"
    }
}

def load_questions():
    questions_by_category = {}
    for category, info in CATEGORY_FILES.items():
        filename = info["file"]
        try:
            dataset = load_dataset(DATASET_NAME, data_files=filename, split="train", token=HF_TOKEN)
            questions_by_category[category] = list(dataset)
            print(f"Loaded {len(questions_by_category[category])} questions from {category}")
        except Exception as e:
            print(f"Failed to load {category}: {e}")
            questions_by_category[category] = []
    return questions_by_category

print("Loading question sets...")
QUESTIONS_BY_CATEGORY = load_questions()

# ========== 通用调用函数（兼容任何 OpenAI 格式 LLM）==========
async def call_model(endpoint: str, model_name: str, question: str, api_key: str = None):
    """
    通用 LLM 调用
    - endpoint: API 地址（如 https://api.openai.com/v1/chat/completions）
    - model_name: 模型名称（如 gpt-3.5-turbo, deepseek-chat, claude-3 等）
    - question: 问题内容
    - api_key: API 密钥
    """
    payload = {
        "model": model_name,  # ← 用户自己填模型名称
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.0
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(endpoint, json=payload, headers=headers)
            if response.status_code == 200:
                resp_data = response.json()
                # 通用解析：支持 OpenAI 格式
                answer = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return answer if answer else "No response content"
            else:
                return f"HTTP Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

def calculate_score(model_answer: str, expected_answer: str) -> float:
    if not model_answer:
        return 0.0
    
    model_lower = model_answer.strip().lower()
    expected_lower = expected_answer.strip().lower()
    
    if model_lower == expected_lower:
        return 1.0
    if expected_lower in model_lower:
        return 1.0
    
    return 0.0

def evaluate_model(endpoint: str, model_name: str, api_key: str, selected_categories: list, num_questions: int):
    """测评函数"""
    if not endpoint:
        return {"error": "请填写模型 API 地址"}
    
    if not model_name:
        return {"error": "请填写模型名称（如 gpt-3.5-turbo）"}
    
    if not api_key:
        return {"error": "请填写 API Key"}
    
    all_questions = []
    for cat in selected_categories:
        if cat in QUESTIONS_BY_CATEGORY:
            qs = QUESTIONS_BY_CATEGORY[cat]
            if qs:
                sample_size = min(num_questions, len(qs))
                selected = random.sample(qs, sample_size)
                for q in selected:
                    all_questions.append({
                        "question": q["question"],
                        "expected": q["answer"],
                        "category": cat
                    })
    
    if not all_questions:
        return {"error": "所选分类中没有可用题目"}
    
    results = []
    for q in all_questions:
        answer = asyncio.run(call_model(endpoint, model_name, q["question"], api_key))
        score = calculate_score(answer, q["expected"])
        
        results.append({
            "question": q["question"][:150] + "..." if len(q["question"]) > 150 else q["question"],
            "category": q["category"],
            "expected": q["expected"],
            "model_answer": answer[:200] + "..." if len(answer) > 200 else answer,
            "score": "✓ 正确" if score == 1.0 else "✗ 错误",
            "score_value": score
        })
    
    total_score = sum(r["score_value"] for r in results)
    accuracy = total_score / len(results) if results else 0
    
    category_stats = {}
    for r in results:
        cat = r["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "correct": 0}
        category_stats[cat]["total"] += 1
        if r["score_value"] == 1.0:
            category_stats[cat]["correct"] += 1
    
    for cat in category_stats:
        cat_stats = category_stats[cat]
        cat_stats["accuracy"] = f"{cat_stats['correct'] / cat_stats['total'] * 100:.1f}%"
    
    return {
        "accuracy": f"{accuracy * 100:.1f}%",
        "total_questions": len(results),
        "correct_count": int(total_score),
        "wrong_count": len(results) - int(total_score),
        "category_stats": category_stats,
        "details": results
    }

# ========== Gradio 界面 ==========
with gr.Blocks(title="Sentiment Evaluation API", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 📊 Sentiment Evaluation API
    ### 测试任意 LLM 的 sentiment 分类能力 (positive / negative / neutral)
    
    **支持任何兼容 OpenAI 格式的 API**：OpenAI、DeepSeek、Together、本地部署的 vLLM 等
    """)
    
    with gr.Row():
        for cat, info in CATEGORY_FILES.items():
            count = len(QUESTIONS_BY_CATEGORY.get(cat, []))
            status = f"✅ {count}题" if count else "⏳ 暂无数据"
            with gr.Column(scale=1):
                gr.Markdown(f"**{cat}**\n{info['description']}\n\n{status}")
    
    with gr.Row():
        with gr.Column(scale=1):
            endpoint = gr.Textbox(
                label="🌐 API 地址",
                placeholder="https://api.openai.com/v1/chat/completions",
                value="https://api.openai.com/v1/chat/completions",
                info="OpenAI 兼容格式的 API 端点"
            )
            model_name = gr.Textbox(
                label="🤖 模型名称",
                placeholder="gpt-3.5-turbo, deepseek-chat, meta-llama/Llama-3-70B...",
                value="gpt-3.5-turbo",
                info="填写模型名称，如 gpt-3.5-turbo、deepseek-chat 等"
            )
            api_key = gr.Textbox(
                label="🔑 API Key",
                placeholder="sk-xxx",
                type="password",
                info="必填：API 密钥"
            )
            categories_checkbox = gr.CheckboxGroup(
                label="📁 选择要测试的分类",
                choices=list(CATEGORY_FILES.keys()),
                value=["equity_news", "country_news"]
            )
            num_questions = gr.Slider(
                label="📝 每个分类抽取题目数",
                minimum=1,
                maximum=10,
                value=3,
                step=1
            )
            submit_btn = gr.Button("🚀 开始测评", variant="primary")
        
        with gr.Column(scale=1):
            output = gr.JSON(label="📈 测评结果")
    
    submit_btn.click(
        fn=evaluate_model,
        inputs=[endpoint, model_name, api_key, categories_checkbox, num_questions],
        outputs=output
    )
    
    gr.Markdown("""
    ---
    ### 💡 使用示例
    
    | 服务商 | API 地址 | 模型名称 |
    |--------|---------|---------|
    | OpenAI | https://api.openai.com/v1/chat/completions | gpt-3.5-turbo / gpt-4 |
    | DeepSeek | https://api.deepseek.com/v1/chat/completions | deepseek-chat |
    | Together | https://api.together.xyz/v1/chat/completions | meta-llama/Llama-3-70B |
    | 本地 vLLM | http://localhost:8000/v1/chat/completions | 你的模型名 |
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
import requests

# Dify API 网址
url = "https://api.dify.ai/v1/workflows/run"

# Dify API 密钥
api_key = "app-Zstm60G7X2h7oBXlmmYzr7V5"



''' @brief：Dify_Api调用函数
    @input_text: 输入文本，为json格式，可以参考示例中的input——text：  
                        input_text = {
                        "need": "Briefing",
                        "tone": None,
                        "word_count": "100",
                        "event": "保险与deepseek",
                        "reference": None,
                        "original_content": None,
                        "restatement_objective": None,  
                        "language": "English",
                        "article_type": None
                    }
                    每个功能需要的输入已经写在input_text中，只需要修改对应的值即可
                    
    @return: 返回的JSON数据，格式参考官网给出格式如下。
            {
                "workflow_run_id": "djflajgkldjgd",
                "task_id": "9da23599-e713-473b-982c-4328d4f5c78a",
                "data": {
                    "id": "fdlsjfjejkghjda",
                    "workflow_id": "fldjaslkfjlsda",
                    "status": "succeeded",
                    "outputs": {
                    "text": "Nice to meet you."
                    },
                    "error": null,
                    "elapsed_time": 0.875,
                    "total_tokens": 3562,
                    "total_steps": 8,
                    "created_at": 1705407629,
                    "finished_at": 1727807631
                }
            }
            
            网页组可以主要关注其中的output，以及error.
            其中 output格式为：
            {
                "Generated Article": null,
                "Restated Article": null,
                "weekly_report": null,
                "Article Summary": null
            }

'''
def Run_Dify( input_text = {}):
    
    headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
    }
    
    request_body = {
    "inputs": input_text,
    "response_mode": "blocking",
    "user": "llmnews"
    }       
    # print("Request Body:", request_body)
    try:
        response = requests.post(url, headers=headers, json=request_body)
        response.raise_for_status()  # 检查 HTTP 错误

        result = response.json()

    except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            print("Response content:", response.text)
            return {"error": str(e)}
    except ValueError as e:
            print(f"Failed to parse JSON response: {e}")
            return {"error": "Failed to parse JSON response"}
            
    return result

# 生成输入文本,可以用这个格式化输入，没有的输入None即可。
def get_input(need, tone, word_count, event, reference, original_content, restatement_objective, language, article_type):
    input_text = {
    "need": need,
    "tone": tone,
    "word_count": word_count,
    "event": event,
    "reference": reference,
    "original_content": original_content,
    "restatement_objective": restatement_objective,  
    "language": language,
    "article_type": article_type
    }
    return input_text


def get_output(need, result):
    output = result["data"]["outputs"]
    if need == "Briefing":
        generated_output = output["weekly_report"]
    elif need == "Article Restatement":
        generated_output = output["Restated Article"]
    elif need == "Article Summary":
        generated_output = output["Article Summary"]
    elif need == "Article Generation":
       generated_output= output["Generated Article"]
    else : generated_output = None
    error = result["data"]["error"]
    
    return generated_output,error

#使用实例，在前端调用直接import就好，防止api泄露
if __name__ == "__main__":
  
    input_text = {
    "need": "Briefing",
    "tone": None,
    "word_count": 100,
    "event": "保险与deepseek",
    "reference": None,
    "original_content": None,
    "restatement_objective": None,  
    "language": "English",
    "article_type": None
}

    input_text = get_input("Briefing", None, 100, "保险与deepseek", None, None, None, "English", None)

    print("Running Dify API")
    result = Run_Dify(input_text)
    print(result)
    print("Dify API finished")    
    
    

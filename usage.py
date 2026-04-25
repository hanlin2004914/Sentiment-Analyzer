from models.router import predict

label = predict("Stock market crashes", model_key="llama")
print(label)

label = predict("Strong earnings report", model_key="opus")
print(label)
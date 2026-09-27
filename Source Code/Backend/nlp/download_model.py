from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import os

NLP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(NLP_DIR, "models")

os.makedirs(MODEL_DIR, exist_ok=True)
print(f"[download_model] Saving DistilBERT model to {MODEL_DIR}...")

# Load pretrained tokenizer and model from Hugging Face and save locally
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

tokenizer.save_pretrained(MODEL_DIR)
model.save_pretrained(MODEL_DIR)

print(f"[download_model] Saved model and tokenizer to {MODEL_DIR}")

import os
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset, Dataset
import pandas as pd

# Paths
NLP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(NLP_DIR, "models")
DATA_DIR = os.path.join(NLP_DIR, "data")

def download_and_prepare_data():
    """
    Simulate downloading and preparing a dataset for phishing/spam detection.
    In a real scenario, this would load from Nazario, Enron, or Kaggle SMS Spam Collection.
    We'll create a small synthetic dataset for demonstration purposes so the script runs.
    """
    print("[PhishGuard NLP] Preparing dataset...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Synthetic data: 1 = Phishing/Spam, 0 = Legitimate/Ham
    data = {
        "text": [
            "URGENT: Your account has been suspended. Click here to verify your identity.",
            "Hey John, are we still on for lunch tomorrow?",
            "You have won a $1000 Walmart gift card! Claim it now before it expires.",
            "Please find the attached invoice for the recent software purchase.",
            "Security Alert: We detected unusual login activity. Reset your password immediately.",
            "The meeting has been rescheduled to 3 PM. See you then."
        ],
        "label": [1, 0, 1, 0, 1, 0]
    }
    
    df = pd.DataFrame(data)
    csv_path = os.path.join(DATA_DIR, "phishing_nlp_dataset.csv")
    df.to_csv(csv_path, index=False)
    
    return load_dataset('csv', data_files={'train': csv_path})['train']

def tokenize_function(examples, tokenizer):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

def train_model():
    print("[PhishGuard NLP] Starting NLP Model Training (DistilBERT)...")
    
    # 1. Load Dataset
    dataset = download_and_prepare_data()
    
    # 2. Load Tokenizer
    tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
    
    # 3. Tokenize Dataset
    print("[PhishGuard NLP] Tokenizing dataset...")
    tokenized_datasets = dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
    
    # 4. Split Dataset (For demo, we just use the whole dataset as train and eval)
    train_dataset = tokenized_datasets
    eval_dataset = tokenized_datasets
    
    # 5. Load Model
    model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)
    
    # 6. Define Training Arguments
    training_args = TrainingArguments(
        output_dir=os.path.join(NLP_DIR, 'results'),
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        num_train_epochs=3,
    )
    
    # 7. Initialize Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
    )
    
    # 8. Train!
    print("[PhishGuard NLP] Training model...")
    trainer.train()
    
    # 9. Save Model
    print(f"[PhishGuard NLP] Saving fine-tuned model to {MODEL_DIR}...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    
    print("[PhishGuard NLP] Training complete!")

if __name__ == "__main__":
    train_model()

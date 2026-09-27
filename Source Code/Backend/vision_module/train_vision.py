import os
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
from torchvision import datasets, models, transforms
from PIL import Image

VISION_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(VISION_DIR, "models")
DATA_DIR = os.path.join(VISION_DIR, "data")

def create_dummy_data():
    """Create a dummy directory structure with fake images if no data exists."""
    print("[PhishGuard Vision] Preparing placeholder dataset structure...")
    for label in ['safe', 'phishing']:
        path = os.path.join(DATA_DIR, 'train', label)
        os.makedirs(path, exist_ok=True)
        # Create a blank image to satisfy torchvision ImageFolder
        if not os.path.exists(os.path.join(path, "dummy.jpg")):
            img = Image.new('RGB', (224, 224), color = (73, 109, 137))
            img.save(os.path.join(path, "dummy.jpg"))

def train_model():
    print("[PhishGuard Vision] Starting Vision Model Training (EfficientNet-B3)...")
    create_dummy_data()

    # Data augmentation and normalization for training
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    print("[PhishGuard Vision] Loading datasets...")
    image_datasets = {
        'train': datasets.ImageFolder(os.path.join(DATA_DIR, 'train'), data_transforms['train'])
    }
    dataloaders = {
        'train': torch.utils.data.DataLoader(image_datasets['train'], batch_size=4, shuffle=True, num_workers=0)
    }

    # Load pre-trained EfficientNet-B3
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.DEFAULT)
    
    # Freeze all layers except the final classifier for fine-tuning
    for param in model.parameters():
        param.requires_grad = False

    num_ftrs = model.classifier[1].in_features
    # We have 2 classes: safe (0) and phishing (1)
    model.classifier[1] = nn.Linear(num_ftrs, 2)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.classifier.parameters(), lr=0.001, momentum=0.9)

    print("[PhishGuard Vision] Training model...")
    model.train()
    for epoch in range(1): # Just 1 epoch for demo
        for inputs, labels in dataloaders['train']:
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
    print(f"[PhishGuard Vision] Saving fine-tuned model to {MODEL_DIR}...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, 'efficientnet_b3_phishguard.pth'))
    
    print("[PhishGuard Vision] Training complete!")

if __name__ == "__main__":
    train_model()

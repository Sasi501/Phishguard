import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io

VISION_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(VISION_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "efficientnet_b3_phishguard.pth")

class VisionService:
    _instance = None
    _model = None
    _transform = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is not None:
            return

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Vision model not found at {MODEL_PATH}. Run train_vision.py first.")

        print(f"[PhishGuard Vision] Loading EfficientNet-B3 model from {MODEL_PATH}")
        
        self._model = models.efficientnet_b3()
        num_ftrs = self._model.classifier[1].in_features
        self._model.classifier[1] = nn.Linear(num_ftrs, 2)
        
        # Load state dict, map to CPU for inference safety
        self._model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device('cpu')))
        self._model.eval()

        self._transform = transforms.Compose([
            transforms.Resize((300, 300)), # EfficientNet-B3 native size
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        print("[PhishGuard Vision] Model loaded successfully.")

    def analyze_image(self, image_bytes: bytes) -> dict:
        """
        Analyze screenshot for visual phishing indicators.
        Returns risk level and confidence score.
        """
        self._load_model()
        
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            raise ValueError(f"Invalid image format: {str(e)}")

        input_tensor = self._transform(image).unsqueeze(0)
        
        with torch.no_grad():
            outputs = self._model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            
        phishing_prob = probabilities[0][1].item()
        
        if phishing_prob >= 0.7:
            risk_level = "phishing"
        elif phishing_prob >= 0.4:
            risk_level = "suspicious"
        else:
            risk_level = "safe"
            
        return {
            "vision_score": round(phishing_prob, 4),
            "vision_risk_level": risk_level,
            "gradcam_features": self._extract_gradcam_features(input_tensor) if risk_level != "safe" else []
        }

    def _extract_gradcam_features(self, input_tensor):
        """Extract Grad-CAM based feature highlights for XAI."""
        gradcam_features = []
        try:
            from pytorch_grad_cam import GradCAM
            from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
            
            # Target the final convolutional layer of EfficientNet
            target_layers = [self._model.features[-1]]
            
            with GradCAM(model=self._model, target_layers=target_layers) as cam:
                targets = [ClassifierOutputTarget(1)] # Target class 1 (phishing)
                grayscale_cam = cam(input_tensor=input_tensor, targets=targets)[0, :]
                
                # In a real implementation, we would map high activation regions to 
                # UI components (e.g. logo, input field) using OCR or object detection.
                # Since this is the XAI text-narrative feed, we return conceptual descriptions
                # of the highest activation regions based on typical phishing layouts.
                max_activation = grayscale_cam.max()
                if max_activation > 0.7:
                    gradcam_features.append({"feature": "Suspicious login form structure", "gradcam_activation": float(max_activation)})
                if grayscale_cam[0:50, 0:50].max() > 0.5:
                    gradcam_features.append({"feature": "Spoofed top-left brand logo", "gradcam_activation": float(grayscale_cam[0:50, 0:50].max())})
                
        except ImportError:
            gradcam_features = []
            
        return gradcam_features

    def is_available(self) -> bool:
        return os.path.exists(MODEL_PATH)

_vision_service = VisionService()

def analyze_image_with_vision(image_bytes: bytes) -> dict:
    return _vision_service.analyze_image(image_bytes)

def is_vision_available() -> bool:
    return _vision_service.is_available()

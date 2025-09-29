"""
Convert ONNX Ultra Lightweight Face Detection model to OpenVINO IR format
"""
import sys
from pathlib import Path
import openvino as ov

def convert_onnx_to_openvino():
    """Convert the ONNX model to OpenVINO IR format"""
    
    # Define paths
    model_dir = Path(__file__).parent / "models" / "ultra-lightweight-face-detection-rfb-320"
    onnx_path = model_dir / "ultra-lightweight-face-detection-rfb-320.onnx"
    output_xml = model_dir / "ultra-lightweight-face-detection-rfb-320.xml"
    output_bin = model_dir / "ultra-lightweight-face-detection-rfb-320.bin"
    
    print(f"Converting ONNX model: {onnx_path}")
    print(f"Output will be: {output_xml} and {output_bin}")
    
    if not onnx_path.exists():
        print(f"ERROR: ONNX model not found at {onnx_path}")
        return False
    
    try:
        # Initialize OpenVINO Core
        core = ov.Core()
        
        # Read the ONNX model
        print("Reading ONNX model...")
        model = core.read_model(str(onnx_path))
        
        # Print model information
        print(f"Model inputs:")
        for input_layer in model.inputs:
            print(f"  - {input_layer.get_any_name()}: {input_layer.get_shape()}")
        
        print(f"Model outputs:")
        for output_layer in model.outputs:
            print(f"  - {output_layer.get_any_name()}: {output_layer.get_shape()}")
        
        # Save the model in OpenVINO IR format
        print("Converting to OpenVINO IR format...")
        ov.save_model(model, str(output_xml))
        
        print(f"✅ Conversion successful!")
        print(f"✅ Created: {output_xml}")
        print(f"✅ Created: {output_bin}")
        
        # Verify the converted model
        print("\nVerifying converted model...")
        converted_model = core.read_model(str(output_xml))
        compiled_model = core.compile_model(converted_model, "CPU")
        
        print("✅ Model verification successful!")
        print(f"✅ Model is ready for use with OpenVINO")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = convert_onnx_to_openvino()
    sys.exit(0 if success else 1)
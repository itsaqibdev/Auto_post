import base64
import os

def create_fonts_file():
    fonts = {
        'ROBOTO_BOLD': 'Roboto-Bold.ttf',
        'ROBOTO_REGULAR': 'Roboto-Regular.ttf'
    }
    
    output_lines = []
    
    for var_name, filename in fonts.items():
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                output_lines.append(f'{var_name} = "{encoded}"')
        else:
            print(f"Warning: {filename} not found")
            return False
            
    with open('fonts_data.py', 'w') as f:
        f.write('\n'.join(output_lines))
    
    print("Successfully created fonts_data.py")
    return True

if __name__ == '__main__':
    create_fonts_file()

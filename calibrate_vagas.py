# calibrate_vagas.py
import cv2
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=str, required=True, help="Caminho do vídeo")
args = parser.parse_args()

drawing = False
start_point = None
end_point = None
vagas = []
current_vaga_id = 1

def mouse_callback(event, x, y, flags, param):
    global drawing, start_point, end_point, current_vaga_id
    
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = (x, y)
        end_point = (x, y)
    
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            end_point = (x, y)
    
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = (x, y)
        
        x1 = min(start_point[0], end_point[0])
        y1 = min(start_point[1], end_point[1])
        x2 = max(start_point[0], end_point[0])
        y2 = max(start_point[1], end_point[1])
        
        vaga_id = f"V{current_vaga_id}"
        vagas.append((vaga_id, (x1, y1, x2, y2)))
        
        print(f"Vaga {vaga_id} definida: ({x1}, {y1}, {x2}, {y2})")
        current_vaga_id += 1
        
        start_point = None

cap = cv2.VideoCapture(args.source)
if not cap.isOpened():
    print("Erro ao abrir video")
    exit(1)

ret, frame = cap.read()
if not ret:
    print("Erro ao ler primeiro frame")
    exit(1)

original = frame.copy()

print("="*60)
print("CALIBRACAO DE VAGAS")
print("="*60)
print("1. Clique e arraste para definir cada vaga")
print("2. Pressione 'r' para resetar")
print("3. Pressione 's' para salvar e sair")
print("4. Pressione 'q' para sair sem salvar")
print("="*60)

cv2.namedWindow('Calibrar Vagas')
cv2.setMouseCallback('Calibrar Vagas', mouse_callback)

while True:
    display = frame.copy()
    
    for vaga_id, (x1, y1, x2, y2) in vagas:
        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(display, vaga_id, (x1+10, y1+30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    if drawing and start_point and end_point:
        cv2.rectangle(display, start_point, end_point, (0, 255, 255), 2)
    
    cv2.putText(display, "R=Reset | S=Salvar | Q=Sair", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(display, f"Vagas definidas: {len(vagas)}", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow('Calibrar Vagas', display)
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        print("\nCalibracao cancelada")
        break
    elif key == ord('r'):
        vagas = []
        current_vaga_id = 1
        frame = original.copy()
        print("\nReset - vagas limpas")
    elif key == ord('s'):
        if len(vagas) == 0:
            print("\nNenhuma vaga definida!")
            continue
        
        print("\n" + "="*60)
        print("CONFIGURACAO SALVA")
        print("="*60)
        print("\nCopie para detect_vagas_fixas.py:\n")
        print("VAGAS = {")
        for vaga_id, (x1, y1, x2, y2) in vagas:
            print(f'    "{vaga_id}": {{"rect": ({x1}, {y1}, {x2}, {y2}), "ocupada": False, "placa": None}},')
        print("}")
        print("\n" + "="*60)
        break

cap.release()
cv2.destroyAllWindows()
# yolo_inference.py

import supervision as sv
from ultralytics import YOLO

class YoloInference:
    def __init__(self, model_path='last.pt', class_names=['fish', 'no_fish']):
        self.model = YOLO(model_path)
        self.class_names = class_names

    def get_labels(self, image_list):
        # Run batched inference on a list of images

        results = self.model(image_list, stream=True)  # return a generator of Results objects

        for result in results:
            detections = sv.Detections.from_ultralytics(result)

            labels = [
                f"{coordinates}, {self.class_names[class_id]}, {confidence:0.2f}"
                for coordinates, _, confidence, class_id, _
                in detections
            ]

            return labels

    # def print_labels(self, image_list):
    #     labels = self.get_labels(image_list)
    #     print(labels)


if __name__ == "__main__":
    inferencer = YoloInference()


    labels = inferencer.get_labels(['1.jpg'])

    # for label in labels:
    #     coordinates, class_name, confidence = label.split(',')

    #     # Clean and parse the data
    #     coordinates = coordinates.strip('[]').split()
    #     x1, y1, x2, y2 = map(float, coordinates)  # Convert string coordinates to float
    #     class_name = class_name.strip()
    #     confidence = float(confidence.strip())  # Convert confidence string to float

    #     # Print the results
    #     print(f"Coordinates: x1={x1:.2f}, y1={y1:.2f}, x2={x2:.2f}, y2={y2:.2f}, Class: {class_name}, Confidence: {confidence:.2f}")

    #     if class_name == 'fish':
    #         print('fish')
    #     elif class_name == 'no_fish':
    #         print('no_fish')
    #     else:
    #         print('nothing')



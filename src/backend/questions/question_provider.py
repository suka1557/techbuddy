import json

class QuestionProvider:
    def __init__(self, file_path: str = None):
        if not file_path:
            raise ValueError("file_path must be provided")
        
        with open(file_path, 'r') as file:
            self.questions = json.load(file)
            self.domains = list(self.questions.keys())

        self.current_index = 0

    def get_next_from_file(self, domain: str = "machine_learning") -> str:
        if domain not in self.questions:
            raise ValueError(f"Domain '{domain}' not found in questions")

        if self.current_index >= len(self.questions[domain]):
            # Loop back to the start or return a "Finished" message
            self.current_index = 0 
            
        question = self.questions[domain][self.current_index]["question"]
        self.current_index += 1
        return question
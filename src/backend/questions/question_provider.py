import json


class QuestionProvider:
    def __init__(self, file_path: str = None):
        if not file_path:
            raise ValueError("file_path must be provided")

        with open(file_path, "r") as file:
            self.questions = json.load(file)
            self.domains = list(self.questions.keys())

        self.current_index = {}
        for domain in self.domains:
            self.current_index[domain] = 0

    def get_domains(self) -> list:
        """Return list of available domains."""
        return self.domains

    def get_next_from_file(self, domain: str = "machine_learning") -> str:
        if domain not in self.questions:
            raise ValueError(f"Domain '{domain}' not found in questions")

        if self.current_index[domain] >= len(self.questions[domain]):
            # Loop back to the start
            self.current_index[domain] = 0

        question = self.questions[domain][self.current_index[domain]]["question"]
        self.current_index[domain] += 1
        return question

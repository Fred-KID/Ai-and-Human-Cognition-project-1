import tkinter as tk
from tkinter import messagebox
import random
import json
import os
import re
from datetime import datetime


# ============================================================
# Configuration
# ============================================================

WORDS_FILE = "words.txt"
DATA_DIRECTORY = "participant_data"

WORD_DISPLAY_TIME = {
    3: 3000,   # Experiment 3 uses 3 seconds
    4: 3000,   # Experiment 4 uses 3 seconds
    5: 3000,
    6: 3000,
    7: 3000,
    8: 3000,
}

SHORT_WORD_DISPLAY_TIME = 1000  # Experiment 2


COLORS = [
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "orange",
    "pink",
    "cyan",
    "brown",
    "gray"
]


# ============================================================
# Utility functions
# ============================================================

def load_words(filename):
    """Load words from words.txt, one word per line."""

    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Could not find {filename}. "
            f"Make sure it is in the same directory as this script."
        )

    with open(filename, "r", encoding="utf-8") as f:
        words = [
            line.strip()
            for line in f
            if line.strip()
        ]

    # Keep alphabetic words only
    words = [
        word for word in words
        if re.fullmatch(r"[A-Za-z]+", word)
    ]

    # Remove duplicates while preserving order
    words = list(dict.fromkeys(words))

    return words


def normalize_word(word):
    """Normalize an answer for comparison."""
    return word.strip().lower()


def parse_responses(text):
    """
    Turn participant input into a list of responses.

    Participants can separate answers by spaces or new lines.
    """
    text = text.replace(",", " ")
    return [
        normalize_word(x)
        for x in text.split()
        if x.strip()
    ]


def unique_filename(participant_id):
    """Create a filename that won't overwrite an existing participant."""

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", participant_id)

    base = os.path.join(
        DATA_DIRECTORY,
        f"participant_{safe_id}"
    )

    filename = base + ".json"

    counter = 2
    while os.path.exists(filename):
        filename = f"{base}_{counter}.json"
        counter += 1

    return filename


def score_free_recall(correct_words, responses):
    """
    Score free recall.

    Each target word can only receive credit once.
    Returns the number correct and the correctly recalled words.
    """

    remaining = set(normalize_word(word) for word in correct_words)

    correct = []

    for response in responses:
        if response in remaining:
            correct.append(response)
            remaining.remove(response)

    return len(correct), correct


def score_ordered_recall(correct_sequence, responses):
    """
    Score ordered recall position-by-position.

    Example:
        Target:    A B C D
        Response:  A X C D

    Score = 3
    """

    score = 0

    for i in range(min(len(correct_sequence), len(responses))):
        if normalize_word(correct_sequence[i]) == normalize_word(responses[i]):
            score += 1

    return score


# ============================================================
# Main application
# ============================================================

class RecallExperiment:

    def __init__(self, root):

        self.root = root
        self.root.title("Memory Recall Experiment")

        # Full-screen experimental window
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="white")

        self.root.bind("<Escape>", self.handle_escape)

        # Load words
        self.all_words = load_words(WORDS_FILE)

        if len(self.all_words) < 80:
            raise ValueError(
                "words.txt does not contain enough words. "
                "At least 80 suitable words are recommended "
                "for the experiments."
            )

        # Shuffle once so words are not deliberately selected
        # in alphabetical/file order.
        random.shuffle(self.all_words)

        # Words already used
        self.used_words = set()

        # Experiment number
        self.current_experiment = 0

        # Participant information
        self.participant_id = None
        self.output_file = None
        self.start_time = datetime.now().isoformat()

        # Results
        self.results = []

        # State
        self.allow_escape = False
        self.current_recall_callback = None

        # Main container
        self.container = tk.Frame(
            self.root,
            bg="white"
        )
        self.container.pack(
            fill="both",
            expand=True
        )

        self.show_participant_screen()

    # --------------------------------------------------------
    # General UI
    # --------------------------------------------------------

    def clear_screen(self, bg="white"):
        for widget in self.container.winfo_children():
            widget.destroy()

        self.container.configure(bg=bg)

    def add_label(
        self,
        text,
        size=28,
        bold=False,
        bg="white",
        fg="black"
    ):
        font = ("Arial", size, "bold" if bold else "normal")

        label = tk.Label(
            self.container,
            text=text,
            font=font,
            bg=bg,
            fg=fg,
            wraplength=1200,
            justify="center"
        )

        label.pack(
            expand=True,
            padx=50,
            pady=30
        )

        return label

    def add_button(self, text, command):
        button = tk.Button(
            self.container,
            text=text,
            command=command,
            font=("Arial", 24),
            padx=40,
            pady=15
        )

        button.pack(pady=20)

        return button

    # --------------------------------------------------------
    # Participant identification
    # --------------------------------------------------------

    def show_participant_screen(self):

        self.clear_screen()

        title = tk.Label(
            self.container,
            text="Memory Recall Experiment",
            font=("Arial", 36, "bold"),
            bg="white"
        )
        title.pack(pady=80)

        instruction = tk.Label(
            self.container,
            text="Please enter the participant ID:",
            font=("Arial", 26),
            bg="white"
        )
        instruction.pack(pady=20)

        self.id_entry = tk.Entry(
            self.container,
            font=("Arial", 28),
            justify="center"
        )
        self.id_entry.pack(pady=20)

        self.id_entry.focus_set()

        self.add_button(
            "Begin",
            self.start_experiment
        )

    def start_experiment(self):

        participant_id = self.id_entry.get().strip()

        if not participant_id:
            messagebox.showwarning(
                "Participant ID",
                "Please enter a participant ID."
            )
            return

        self.participant_id = participant_id

        os.makedirs(
            DATA_DIRECTORY,
            exist_ok=True
        )

        self.output_file = unique_filename(
            participant_id
        )

        self.current_experiment = 1

        self.run_experiment()

    # --------------------------------------------------------
    # Word selection
    # --------------------------------------------------------

    def get_new_words(self, number, three_letter_only=False):

        available = []

        for word in self.all_words:

            normalized = normalize_word(word)

            if normalized in self.used_words:
                continue

            if three_letter_only and len(normalized) != 3:
                continue

            available.append(word)

        if len(available) < number:
            raise ValueError(
                "There are not enough unused words in words.txt "
                "to continue the experiment."
            )

        selected = random.sample(
            available,
            number
        )

        for word in selected:
            self.used_words.add(
                normalize_word(word)
            )

        return selected

    # --------------------------------------------------------
    # Experiment sequencing
    # --------------------------------------------------------

    def run_experiment(self):

        self.allow_escape = False

        if self.current_experiment == 1:
            self.experiment_1()

        elif self.current_experiment == 2:
            self.experiment_2()

        elif self.current_experiment == 3:
            self.experiment_3()

        elif self.current_experiment == 4:
            self.experiment_4()

        elif self.current_experiment == 5:
            self.experiment_5()

        elif self.current_experiment == 6:
            self.experiment_6()

        elif self.current_experiment == 7:
            self.experiment_7()

        elif self.current_experiment == 8:
            self.experiment_8()

        else:
            self.finish_experiment()

    # --------------------------------------------------------
    # Experiment instructions
    # --------------------------------------------------------

    def show_instructions(self, text, callback):

        self.clear_screen()

        self.add_label(
            f"Experiment {self.current_experiment}\n\n{text}",
            size=30
        )

        self.add_button(
            "Begin",
            callback
        )

    # ========================================================
    # Experiment 1
    # ========================================================

    def experiment_1(self):

        instructions = (
            "You will be shown 12 words in sequence.\n\n"
            "When prompted, please write down as many of "
            "the 12 as you can recall.\n\n"
            "They do not need to be in order."
        )

        self.show_instructions(
            instructions,
            self.start_experiment_1
        )

    def start_experiment_1(self):

        words = self.get_new_words(12)

        self.present_words(
            words,
            3000,
            lambda: self.show_free_recall(
                words,
                experiment=1
            )
        )

    # ========================================================
    # Experiment 2
    # ========================================================

    def experiment_2(self):

        instructions = (
            "You will once again be shown 12 words in sequence, "
            "this time with shorter intervals.\n\n"
            "When prompted, please write down as many of the "
            "12 as you can recall.\n\n"
            "They do not need to be in order."
        )

        self.show_instructions(
            instructions,
            self.start_experiment_2
        )

    def start_experiment_2(self):

        words = self.get_new_words(15)

        self.present_words(
            words,
            SHORT_WORD_DISPLAY_TIME,
            lambda: self.show_free_recall(
                words,
                experiment=2
            )
        )

    # ========================================================
    # Experiment 3
    # ========================================================

    def experiment_3(self):

        instructions = (
            "Like experiment one you will be shown a list of words to recall. They do not need to be in order.\n\n"
            "This time you "
            "will be show a series of colors after the sequence.\n\n"
            "Please remember the sequence in which they are shown"
        )

        self.show_instructions(
            instructions,
            self.start_experiment_3
        )

    def start_experiment_3(self):

        words = self.get_new_words(12)

        self.present_words(
            words,
            3000,
            lambda: self.show_color_task(
                words
            )
        )

    def show_color_task(self, words):

        colors = random.sample(
            COLORS,
            3
        )

        self.clear_screen()

        self.color_sequence = colors
        self.color_index = 0

        self.show_next_color(
            words
        )

    def show_next_color(self, words):

        if self.color_index >= len(self.color_sequence):

            # Brief blank screen before recall
            self.clear_screen()

            self.root.after(
                4000,
                lambda: self.show_free_recall(
                    words,
                    experiment=3,
                    additional_data={
                        "distractor_colors":
                            self.color_sequence
                    }
                )
            )

            return

        color = self.color_sequence[
            self.color_index
        ]

        self.clear_screen(
            bg=color
        )

        self.color_index += 1

        self.root.after(
            1000,
            lambda: self.show_next_color(
                words
            )
        )

    # ========================================================
    # Experiment 4
    # ========================================================

    def experiment_4(self):

        instructions = (
            "Once again, you will be shown a series of words to recall in any order\n\n"
            "After the sequence there will be a delay of 30 seconds \n\n"
            "Then you will be asked to recall the words."
        )

        self.show_instructions(
            instructions,
            self.start_experiment_4
        )

    def start_experiment_4(self):

        words = self.get_new_words(12)

        self.present_words(
            words,
            3000,
            lambda: self.blank_delay(
                words
            )
        )

    def blank_delay(self, words):

        self.clear_screen(
            bg="white"
        )

        # Exactly 30 seconds
        self.root.after(
            30000,
            lambda: self.show_free_recall(
                words,
                experiment=4,
                additional_data={
                    "blank_delay_seconds": 30
                }
            )
        )

    # ========================================================
    # Experiment 5
    # ========================================================

    def experiment_5(self):

        instructions = (
            "You will be shown 10 words in a sequence.\n\n"
            "When prompted, please recall as many words as you "
            "can in the order that was shown.\n\n"
            "Do not skip words, as they need to be in the "
            "exact order shown.\n\n"
        )

        self.show_instructions(
            instructions,
            self.start_experiment_5
        )

    def start_experiment_5(self):

        words = self.get_new_words(
            10,
            three_letter_only=True
        )

        self.present_words(
            words,
            3000,
            lambda: self.show_ordered_recall(
                words,
                experiment=5
            )
        )

    # ========================================================
    # Experiment 6
    # ========================================================

    def experiment_6(self):

        instructions = (
            "You will be shown 10 3-letter triplets.\n\n"
            "When prompted, please recall as many triplets as "
            "you can in the order that was shown.\n\n"
            "Do not skip any, as they need to be in the "
            "exact order shown.\n\n"
        )

        self.show_instructions(
            instructions,
            self.start_experiment_6
        )

    def start_experiment_6(self):

        triplets = []

        consonants = "BCDFGHJKLMNPQRSTVWXYZ"

        while len(triplets) < 10:

            triplet = "".join(
                random.choice(consonants)
                for _ in range(3)
            )

            if triplet not in triplets:
                triplets.append(triplet)

        self.present_words(
            triplets,
            3000,
            lambda: self.show_ordered_recall(
                triplets,
                experiment=6
            )
        )

    # ========================================================
    # Experiment 7
    # ========================================================

    def experiment_7(self):

        instructions = (
            "You will be shown 10 words in a sequence.\n\n"
            "While the words are being shown, repeat out loud to yourself:\n\n"
            "\"fah-lah-fah-lah...\"\n\n"
            "Continue doing this while viewing the words.\n\n"
            "When prompted, recall as many words as you can "
            "in the order that was shown.\n\n"
            "Do not skip words, as they need to be in the "
            "exact order shown.\n\n"
        )

        self.show_instructions(
            instructions,
            self.start_experiment_7
        )

    def start_experiment_7(self):

        words = self.get_new_words(
            10,
            three_letter_only=True
        )

        self.present_words(
            words,
            3000,
            lambda: self.show_ordered_recall(
                words,
                experiment=7
            )
        )

    # ========================================================
    # Experiment 8
    # ========================================================

    def experiment_8(self):

        instructions = (
            "You will be shown 10 words in a sequence.\n\n"
            "While the words are being shown, tap your fingers "
            "in a constant pattern of your choosing.\n\n"
            "Continue tapping while viewing the words.\n\n"
            "When prompted, recall as many words as you can "
            "in the order that was shown.\n\n"
            "Do not skip words, as they need to be in the "
            "exact order shown.\n\n"
        )

        self.show_instructions(
            instructions,
            self.start_experiment_8
        )

    def start_experiment_8(self):

        words = self.get_new_words(
            10,
            three_letter_only=True
        )

        self.present_words(
            words,
            3000,
            lambda: self.show_ordered_recall(
                words,
                experiment=8
            )
        )

    # ========================================================
    # Word presentation
    # ========================================================

    def present_words(
        self,
        words,
        interval,
        callback
    ):

        self.clear_screen()

        self.presentation_words = words
        self.presentation_interval = interval
        self.presentation_callback = callback
        self.presentation_index = 0

        self.show_next_word()

    def show_next_word(self):

        if self.presentation_index >= len(
            self.presentation_words
        ):

            self.clear_screen()

            # Small blank interval before recall
            self.root.after(
                500,
                self.presentation_callback
            )

            return

        word = self.presentation_words[
            self.presentation_index
        ]

        self.clear_screen()

        self.add_label(
            word,
            size=60,
            bold=True
        )

        self.presentation_index += 1

        self.root.after(
            self.presentation_interval,
            self.show_next_word
        )

    # ========================================================
    # Free recall
    # ========================================================

    def show_free_recall(
        self,
        correct_words,
        experiment,
        additional_data=None
    ):

        self.clear_screen()

        self.allow_escape = True

        self.current_recall_callback = None

        self.add_label(
            "Recall",
            size=36,
            bold=True
        )

        instructions = tk.Label(
            self.container,
            text=(
                "Type as many words as you remember.\n"
                "Separate words with spaces or new lines.\n\n"
            ),
            font=("Arial", 22),
            bg="white"
        )
        instructions.pack(pady=10)

        text_box = tk.Text(
            self.container,
            font=("Arial", 24),
            height=8,
            width=60
        )
        text_box.pack(
            padx=50,
            pady=20
        )

        text_box.focus_set()

        def submit():

            self.allow_escape = False

            responses = parse_responses(
                text_box.get("1.0", tk.END)
            )

            score, correct = score_free_recall(
                correct_words,
                responses
            )

            result = {
                "experiment": experiment,
                "type": "free_recall",
                "stimuli": correct_words,
                "responses": responses,
                "correct_responses": correct,
                "score": score,
                "maximum_score": len(correct_words),
                "skipped": False
            }

            if additional_data:
                result.update(
                    additional_data
                )

            self.results.append(result)

            self.save_data()

            self.next_experiment()

        self.add_button(
            "Submit Recall",
            submit
        )

        self.current_recall_callback = submit

    # ========================================================
    # Ordered recall
    # ========================================================

    def show_ordered_recall(
        self,
        correct_sequence,
        experiment
    ):

        self.clear_screen()

        self.allow_escape = True

        self.add_label(
            "Recall the sequence",
            size=36,
            bold=True
        )

        instructions = tk.Label(
            self.container,
            text=(
                "Enter the words/triplets in the order shown.\n"
                "Separate each answer with spaces "
                "or new lines.\n\n"
            ),
            font=("Arial", 22),
            bg="white"
        )
        instructions.pack(pady=10)

        text_box = tk.Text(
            self.container,
            font=("Arial", 24),
            height=6,
            width=60
        )
        text_box.pack(
            padx=50,
            pady=20
        )

        text_box.focus_set()

        def submit():

            self.allow_escape = False

            responses = parse_responses(
                text_box.get("1.0", tk.END)
            )

            score = score_ordered_recall(
                correct_sequence,
                responses
            )

            result = {
                "experiment": experiment,
                "type": "ordered_recall",
                "stimuli": correct_sequence,
                "responses": responses,
                "score": score,
                "maximum_score": len(correct_sequence),
                "skipped": False
            }

            self.results.append(result)

            self.save_data()

            self.next_experiment()

        self.add_button(
            "Submit Recall",
            submit
        )

        self.current_recall_callback = submit

    # ========================================================
    # Escape handling
    # ========================================================

    def handle_escape(self, event=None):

        if not self.allow_escape:
            return

        self.allow_escape = False

        # Record that the recall was skipped.
        result = {
            "experiment": self.current_experiment,
            "type": "skipped",
            "responses": [],
            "score": 0,
            "maximum_score": (
                15 if self.current_experiment <= 4
                else 10
            ),
            "skipped": True
        }

        self.results.append(result)

        self.save_data()

        self.next_experiment()

    # ========================================================
    # Moving to next experiment
    # ========================================================

    def next_experiment(self):

        self.current_experiment += 1

        if self.current_experiment <= 8:

            self.root.after(
                500,
                self.run_experiment
            )

        else:

            self.root.after(
                500,
                self.finish_experiment
            )

    # ========================================================
    # Saving
    # ========================================================

    def save_data(self):
        """Save the participant's current data to a JSON file."""

        data = {
            "participant_id": self.participant_id,
            "date_started": self.start_time,
            "last_saved": datetime.now().isoformat(),
            "experiments": self.results
        }

        # Make sure the output directory exists.
        os.makedirs(DATA_DIRECTORY, exist_ok=True)

        # Write JSON safely and readably.
        with open(
            self.output_file,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )
    def finish_experiment(self):
        """Finish the experiment and display the completion screen."""

        self.allow_escape = False

        # Make one final save.
        self.save_data()

        self.clear_screen()

        self.add_label(
            "Experiment Complete",
            size=40,
            bold=True
        )

        self.add_label(
            "Thank you for participating.\n\n"
            "Your responses have been saved.",
            size=26
        )

        self.add_button(
            "Exit",
            self.root.destroy
        )

def main():
    root = tk.Tk()
    RecallExperiment(root)
    root.mainloop()


if __name__ == "__main__":
    main()
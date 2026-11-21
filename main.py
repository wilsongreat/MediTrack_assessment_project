"""MediTrack text-based application. Run with: python3 main.py"""

import getpass
import os
import sys



from core import MediTrack,MediTrackError, check_password, clean_text


# The data file sits in the same folder as this file.
APP_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_FOLDER, "meditrack_data.json")

# A special error we raise when the user types "cancel" at any question.
# The menu catches it, prints "Cancelled." and shows the menu again.
class CancelledInput(Exception):
    pass


# ----- Asking questions -----

# Asks for a password. getpass hides what the user types, so the password
def ask(question):
    answer = input(question + ": ").strip()
    if answer.lower() == "cancel":
        raise CancelledInput()
    return answer

# Asks for a password. getpass hides what the user types, so the password
# never shows on screen
def ask_password(question):
    answer = getpass.getpass(question + ": ")
    if answer.lower() == "cancel":
        raise CancelledInput()
    return answer


# Asks for a piece of text such as a name, and keeps asking until it is valid.
def ask_text(question, label):
    while True:
        answer = ask(question)
        try:
            return clean_text(answer, label)
        except MediTrackError as error:
            print(f"  {error}")


# TextApp is the whole text-based app. It remembers the data (tracker),
# where to save it (path) and who is signed in (user).
class TextApp:

    # Sets up the app. Nobody is signed in when the app starts, so user is None.
    def __init__(self, tracker, path):
        self.tracker = tracker  # Holds all the records and the rules.
        self.path = path  # Where the JSON data file is saved.
        self.user = None  # The signed-in professional, or None.



    # Runs the app. It shows the start menu until someone signs in, then the
    # signed-in menu until they sign out, and repeats until the user exits.
    def run(self):
        print("MediTrack: appointments and prescriptions. Type 'cancel' at any prompt to go back.")
        while True:
            if self.user is None:
                signed_in = self.start_menu()
                if not signed_in:
                    print("Goodbye.")
                    return
            else:
                self.signed_in_menu()

        
    def start_menu(self):
        """Shows the start menu until someone signs in or exits. Returns True if signed in, False if exited."""
        while True:
            print("Welcome. Sign up or sign in.")
            print("1. Sign up")
            print("2. Sign in")
            print("3. Exit")
        
            choice = input("Choose an option: ").strip()
            if choice == "0":
             return False
            print()
            try:
                if choice == "1":
                    self.sign_up()
                elif choice == "2":
                    self.sign_in()
                else:
                    print("Please enter a number from 0 to 2.")
            except CancelledInput:
                print("Cancelled.")
            except MediTrackError as error:
                print(f"Could not do that: {error}")
        return True  

    # Shows who is signed in. For now the only option is to sign out,
    # which sets user back to None and returns to the start menu.
    def signed_in_menu(self):
        while True:
            print()
            print(f"Signed in as {self.user.name} ({self.user.id}).")
            print(" 0. Sign out")
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print(f"Signed out {self.user.name}.")
                self.user = None
                return
            print("Please enter 0 to sign out.")

    # Prints a message about what changed, then saves all the data to the JSON file. 
    def save(self, message):
        print(message)
        self.tracker.save(self.path)

   # Creates a new account, then signs the new user in.
    def sign_up(self):
        name = ask_text("Name", "Name")
        specialty = ask_text("Specialty", "Specialty")

        while True:
            email = ask("Email")
            try:
                email = self.tracker.check_email_available(email)
                break
            except MediTrackError as error:
                print(f"  {error}")

        while True:
            password = ask_password("Password (10 to 128 characters)")
            try:
                check_password(password)
                break
            except MediTrackError as error:
                print(f"  {error}")

        while True:
            confirm = ask_password("Confirm password")
            if confirm == password:
                break
            print("  Passwords do not match. Type the same password again.")

        professional = self.tracker.create_account(name, specialty, email, password)
        self.save(f"Created account {email} for {professional.name} ({professional.id}).")
        self.user = professional

    # Signs in an existing user. If the email is not found or the password is wrong, it prints an error and returns to the start menu.
    def sign_in(self):
        email = ask("Email")
        password = ask_password("Password")
        try:
            professional = self.tracker.sign_in(email, password)
            self.user = professional
            print(f"Signed in {professional.name} ({professional.id}).")
        except MediTrackError as error:
            print(f"Could not sign in: {error}")




def main():
    try:
        tracker = MediTrack.load(DATA_FILE)
    except MediTrackError as error:
        print(error)
        print("Fix or move the file, then try again. It has not been changed.")
        return 1

    try:
        app = TextApp(tracker, DATA_FILE)
        app.run()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Core logic for MediTrack, shared by the text app (main.py) and the GUI (gui.py)."""

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from dataclasses import dataclass

# ----- Settings -----

FILE_VERSION = 2 
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
EMAIL_MAX_LENGTH = 254
HASH_ITERATIONS = 600_000  
SALT_BYTES = 16 

# removes spaces.and checks that the email looks like proper
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ----- Errors -----
# The apps catch MediTrackError and show its message to the user.

# The base error for anything the user should be told about.
class MediTrackError(Exception):
    pass


# Something the user typed is missing or not valid.
class ValidationError(MediTrackError):
    pass


# A record that was asked for does not exist.
class NotFoundError(MediTrackError):
    pass


# The action clashes with something that already exists, like a used email.
class ConflictError(MediTrackError):
    pass


# The data file could not be read or written.
class DataFileError(MediTrackError):
    pass


# The email and password do not match an account.
class AuthenticationError(MediTrackError):
    pass


# ----- Checking input -----


# Tidies a piece of text: removes extra spaces at the start, end and middle.
def clean_text(value, label, max_length=100):
    text = " ".join(str(value).split())
    if text == "":
        raise ValidationError(f"{label} is required.")
    if len(text) > max_length:
        raise ValidationError(f"{label} must be {max_length} characters or fewer.")
    return text


# Checks an email looks valid and returns it in lower case, so that
def parse_email(value):
    email = str(value).strip().lower()
    if email == "":
        raise ValidationError("Email is required.")
    if len(email) > EMAIL_MAX_LENGTH or not EMAIL_PATTERN.match(email):
        raise ValidationError("Email must look like name@example.com.")
    return email


# Checks a password is between 10 and 128 characters and returns it unchanged.
def check_password(value):
    password = str(value)
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise ValidationError(
            f"Password must be {PASSWORD_MIN_LENGTH} to {PASSWORD_MAX_LENGTH} characters."
        )
    return password


# Turns a password and a salt into a hash, using PBKDF2-SHA256 from Python's
def hash_password(password, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


# ----- Records ----

# A medical professional. Every account belongs to one professional.
@dataclass
class Professional:
    id: str  # Like "PRO-0001".
    name: str
    specialty: str


# The sign-in details for one professional.
@dataclass
class Account:
    email: str
    professional_id: str
    salt: str
    password_hash: str
    iterations: int

    # Returns True if password is the right password for this account.

    def matches(self, password):
        salt = bytes.fromhex(self.salt)
        expected = bytes.fromhex(self.password_hash)
        actual = hash_password(password, salt, self.iterations)
        return hmac.compare_digest(actual, expected)


# ----- The tracker -----


# MediTrack holds every professional and account, and the rules for them.
class MediTrack:

    # Starts with no records. Dictionaries let us find a record quickly
    # by its key: professionals by ID, accounts by email.
    def __init__(self):
        self.professionals = {}
        self.accounts = {}
        self.last_professional_number = 0  

    # Finds a professional by ID
    def get_professional(self, professional_id):
        key = str(professional_id).strip().upper()
        if key not in self.professionals:
            raise NotFoundError(f"Professional '{professional_id}' was not found.")
        return self.professionals[key]

    # Makes the next professional ID: PRO-0001, then PRO-0002, and so on.
    def new_professional_id(self):
        self.last_professional_number = self.last_professional_number + 1
        return f"PRO-{self.last_professional_number:04d}"

    # Checks an email is valid and that no account uses it yet.
    def check_email_available(self, email):
        clean_email = parse_email(email)
        if clean_email in self.accounts:
            raise ConflictError("An account with that email already exists.")
        return clean_email

    # Signs up a new professional and returns them.
    def create_account(self, name, specialty, email, password):
        clean_name = clean_text(name, "Name")
        clean_specialty = clean_text(specialty, "Specialty")
        clean_email = self.check_email_available(email)
        clean_password = check_password(password)

        professional = Professional(self.new_professional_id(), clean_name, clean_specialty)
        self.professionals[professional.id] = professional

        salt = secrets.token_bytes(SALT_BYTES)
        password_hash = hash_password(clean_password, salt, HASH_ITERATIONS)
        account = Account(
            clean_email, professional.id, salt.hex(), password_hash.hex(), HASH_ITERATIONS
        )
        self.accounts[clean_email] = account
        return professional

    # Signs in: returns the professional if the email and password match.
    def sign_in(self, email, password):
        clean_email = str(email).strip().lower()
        if clean_email not in self.accounts:
            hash_password(str(password), bytes(SALT_BYTES), HASH_ITERATIONS)
            raise AuthenticationError("Email or password is incorrect.")
        account = self.accounts[clean_email]
        if not account.matches(str(password)):
            raise AuthenticationError("Email or password is incorrect.")
        return self.get_professional(account.professional_id)

    # ----- Saving and loading -----

    # Saves every professional and account to the JSON file at path.
    def save(self, path):
        professionals = []
        for professional in self.professionals.values():
            professionals.append(vars(professional))
        accounts = []
        for account in self.accounts.values():
            accounts.append(vars(account))
        data = {"version": FILE_VERSION, "professionals": professionals, "accounts": accounts}

        folder = os.path.dirname(os.path.abspath(path))
        temp_path = None
        try:
            os.makedirs(folder, exist_ok=True)
            # mkstemp makes a file only its owner can read and write.
            handle, temp_path = tempfile.mkstemp(dir=folder, suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            os.replace(temp_path, path)
        except OSError as error:
            if temp_path is not None and os.path.exists(temp_path):
                os.remove(temp_path)
            raise DataFileError(f"Could not save '{path}': {error}") from error

    # Loads a tracker from the JSON file at path and returns it.
    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            return cls.from_data(data)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, MediTrackError) as error:
            raise DataFileError(f"Could not load '{path}': {error}") from error

    # Builds a tracker from the data read out of the JSON file.
    @classmethod
    def from_data(cls, data):
        if data["version"] != FILE_VERSION:
            raise ValidationError(f"unsupported file version {data['version']}")
        tracker = cls()
        for item in data["professionals"]:
            tracker.load_professional(item)
        for item in data["accounts"]:
            tracker.load_account(item)
        return tracker

    # Checks one professional from the file and adds it.
    def load_professional(self, item):
        professional_id = str(item["id"])
        prefix, _, number = professional_id.partition("-")
        if prefix != "PRO" or not number.isdigit():
            raise ValidationError(f"unexpected ID '{professional_id}'")
        if professional_id in self.professionals:
            raise ValidationError(f"duplicate ID '{professional_id}'")
        professional = Professional(
            professional_id,
            clean_text(item["name"], "Name"),
            clean_text(item["specialty"], "Specialty"),
        )
        self.professionals[professional_id] = professional
        if int(number) > self.last_professional_number:
            self.last_professional_number = int(number)

    # Checks one account from the file and adds it
    def load_account(self, item):
        email = parse_email(item["email"])
        professional = self.get_professional(item["professional_id"])
        salt = bytes.fromhex(item["salt"]).hex()
        password_hash = bytes.fromhex(item["password_hash"]).hex()
        iterations = int(item["iterations"])
        if iterations < 1:
            raise ValidationError("iterations must be at least 1")
        if email in self.accounts:
            raise ValidationError(f"duplicate account email '{email}'")
        for account in self.accounts.values():
            if account.professional_id == professional.id:
                raise ValidationError(f"{professional.id} has more than one account")
        self.accounts[email] = Account(email, professional.id, salt, password_hash, iterations)

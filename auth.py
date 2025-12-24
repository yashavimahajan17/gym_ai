import bcrypt
from db import users_collection


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def signup_user(username: str, email: str, password: str, name: str) -> dict:
    """
    Create a new user account.
    
    Args:
        username: Unique username for the user
        email: User's email address
        password: Plain text password (will be hashed)
        name: User's full name
        
    Returns:
        dict: User document if successful, None if username already exists
    """
    # Check if username already exists
    existing_user = users_collection.find_one({"_id": {"$eq": username}})
    if existing_user:
        return None
    
    # Hash the password
    password_hash = hash_password(password)
    
    # Create user document
    user_doc = {
        "_id": username,
        "email": email,
        "password": password_hash,
        "name": name
    }
    
    # Insert into database
    users_collection.insert_one(user_doc)
    
    return user_doc


def get_user(username: str) -> dict:
    """
    Retrieve a user by username.
    
    Args:
        username: Username to look up
        
    Returns:
        dict: User document if found, None otherwise
    """
    return users_collection.find_one({"_id": {"$eq": username}})


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username to authenticate
        password: Plain text password to verify
        
    Returns:
        bool: True if authentication successful, False otherwise
    """
    user = get_user(username)
    if not user:
        return False
    
    return verify_password(password, user["password"])


def get_all_users() -> dict:
    """
    Get all users formatted for streamlit-authenticator.
    
    Returns:
        dict: Dictionary of users in the format expected by streamlit-authenticator
    """
    users = list(users_collection.find())
    
    # Format for streamlit-authenticator
    user_dict = {
        "usernames": {}
    }
    
    for user in users:
        user_dict["usernames"][user["_id"]] = {
            "email": user["email"],
            "name": user["name"],
            "password": user["password"]
        }
    
    return user_dict


def update_user_email(username: str, new_email: str) -> bool:
    """
    Update a user's email address.
    
    Args:
        username: Username of the user to update
        new_email: New email address
        
    Returns:
        bool: True if successful, False otherwise
    """
    result = users_collection.update_one(
        {"_id": username},
        {"$set": {"email": new_email}}
    )
    return result.modified_count > 0


def update_user_password(username: str, new_password: str) -> bool:
    """
    Update a user's password.
    
    Args:
        username: Username of the user to update
        new_password: New plain text password (will be hashed)
        
    Returns:
        bool: True if successful, False otherwise
    """
    password_hash = hash_password(new_password)
    result = users_collection.update_one(
        {"_id": username},
        {"$set": {"password": password_hash}}
    )
    return result.modified_count > 0

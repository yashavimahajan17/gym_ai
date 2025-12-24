import streamlit as st
import extra_streamlit_components as stx
import time
from ai import ask_ai, get_macros
from profiles import create_profile, get_notes, get_profile
from form_submit import update_personal_info, add_note, delete_note
from auth import signup_user, authenticate_user, get_user

st.set_page_config(page_title="Personal Fitness Tool", page_icon="💪", layout="wide")

# Initialize cookie manager with a consistent key for reliable persistence
cookie_manager = stx.CookieManager(key="fitness_app_cookies")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "cookies_loaded" not in st.session_state:
    st.session_state.cookies_loaded = False
if "rerun_count" not in st.session_state:
    st.session_state.rerun_count = 0

st.session_state.rerun_count += 1

# Minimum reruns to wait for cookie component to fully initialize
# This addresses the race condition where cookies aren't ready on first renders
MIN_RERUNS_FOR_COOKIES = 4

# Check for existing session cookie on app load
# Always check cookies if not authenticated (cookies load after first render)
if not st.session_state.authenticated:
    cookies = cookie_manager.get_all()
    
    # Check if cookies are loaded and if fitness_app_user exists
    if cookies and "fitness_app_user" in cookies:
        stored_username = cookies.get("fitness_app_user")
        
        # Verify user still exists in database
        if stored_username and get_user(stored_username):
            st.session_state.authenticated = True
            st.session_state.username = stored_username
            st.session_state.cookies_loaded = True
            st.rerun()
        else:
            st.session_state.cookies_loaded = True
    elif cookies is None or len(cookies) == 0:
        # Cookies component not ready yet OR empty - wait for minimum reruns
        if st.session_state.rerun_count >= MIN_RERUNS_FOR_COOKIES:
            st.session_state.cookies_loaded = True
    else:
        # Cookies have some keys but no fitness_app_user
        # Only mark as "loaded" after minimum reruns to avoid race condition
        if st.session_state.rerun_count >= MIN_RERUNS_FOR_COOKIES:
            st.session_state.cookies_loaded = True


@st.fragment()
def personal_data_form():
    with st.form("personal_data"):
        st.header("Personal Data")

        profile = st.session_state.profile

        name = st.text_input("Name", value=profile["general"]["name"])
        age = st.number_input(
            "Age", min_value=1, max_value=120, step=1, value=profile["general"]["age"]
        )
        weight = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            max_value=300.0,
            step=0.1,
            value=float(profile["general"]["weight"]),
        )
        height = st.number_input(
            "Height (cm)",
            min_value=0.0,
            max_value=250.0,
            step=0.1,
            value=float(profile["general"]["height"]),
        )
        genders = ["Male", "Female"]
        gender = st.radio(
            "Gender", genders, genders.index(profile["general"].get("gender", "Male"))
        )
        activities = (
            "Sedentary",
            "Lightly Active",
            "Moderately Active",
            "Very Active",
            "Super Active",
        )
        activity_level = st.selectbox(
            "Activity Level",
            activities,
            index=activities.index(
                profile["general"].get("activity_level", "Sedentary")
            ),
        )

        personal_data_submit = st.form_submit_button("Save")
        if personal_data_submit:
            if all([name, age, weight, height, gender, activity_level]):
                with st.spinner():
                    st.session_state.profile = update_personal_info(
                        profile,
                        "general",
                        name=name,
                        weight=weight,
                        height=height,
                        gender=gender,
                        age=age,
                        activity_level=activity_level,
                    )
                    st.success("Information saved.")
            else:
                st.warning("Please fill in all of the data!")


@st.fragment()
def goals_form():
    profile = st.session_state.profile
    with st.form("goals_form"):
        st.header("Goals")
        goals = st.multiselect(
            "Select your Goals",
            ["Muscle Gain", "Fat Loss", "Stay Active"],
            default=profile.get("goals", ["Muscle Gain"]),
        )

        goals_submit = st.form_submit_button("Save")
        if goals_submit:
            if goals:
                with st.spinner():
                    st.session_state.profile = update_personal_info(
                        profile, "goals", goals=goals
                    )
                    st.success("Goals updated")
            else:
                st.warning("Please select at least one goal.")


@st.fragment()
def macros():
    profile = st.session_state.profile
    nutrition = st.container(border=True)
    nutrition.header("Macros")
    if nutrition.button("Generate with AI"):
        with st.spinner("Generating macros with AI..."):
            try:
                result = get_macros(profile.get("general"), profile.get("goals"))
                profile["nutrition"] = result
                st.session_state.profile = profile
                nutrition.success("AI has generated the results.")
                st.rerun()
            except Exception as e:
                nutrition.error(f"Error generating macros: {e}")

    with nutrition.form("nutrition_form", border=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            calories = st.number_input(
                "Calories",
                min_value=0,
                step=1,
                value=profile["nutrition"].get("calories", 0),
            )
        with col2:
            protein = st.number_input(
                "Protein",
                min_value=0,
                step=1,
                value=profile["nutrition"].get("protein", 0),
            )
        with col3:
            fat = st.number_input(
                "Fat",
                min_value=0,
                step=1,
                value=profile["nutrition"].get("fat", 0),
            )
        with col4:
            carbs = st.number_input(
                "Carbs",
                min_value=0,
                step=1,
                value=profile["nutrition"].get("carbs", 0),
            )

        if st.form_submit_button("Save"):
            with st.spinner():
                st.session_state.profile = update_personal_info(
                    profile,
                    "nutrition",
                    protein=protein,
                    calories=calories,
                    fat=fat,
                    carbs=carbs,
                )
                st.success("Information saved")

@st.fragment()
def notes():
    st.subheader("Notes: ")
    for i, note in enumerate(st.session_state.notes):
        cols = st.columns([5, 1])
        with cols[0]:
            st.text(note.get("text"))
        with cols[1]:
            if st.button("Delete", key=i):
                delete_note(note.get("_id"))
                st.session_state.notes.pop(i)
                st.rerun()
    
    # Use a counter to reset the input widget
    if "note_input_key" not in st.session_state:
        st.session_state.note_input_key = 0
    
    new_note = st.text_input("Add a new note: ", key=f"new_note_{st.session_state.note_input_key}")
    if st.button("Add Note"):
        if new_note:
            note = add_note(new_note, st.session_state.profile_id)
            st.session_state.notes.append(note)
            st.session_state.note_input_key += 1
            st.rerun()

@st.fragment()
def ask_ai_func():
    st.subheader('Ask AI')
    user_question = st.text_input("Ask AI a question: ")
    if st.button("Ask AI"):
        with st.spinner():
            result = ask_ai(st.session_state.profile, user_question)
            st.write(result)

def login_page():
    """Display login form."""
    st.title("🏋️ Personal Fitness Tool")
    st.subheader("Login to Your Account")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username and password:
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.cookies_loaded = True
                    
                    # Set cookie for persistent session (expires in 30 days)
                    cookie_manager.set("fitness_app_user", username, max_age=30*24*60*60, path="/")
                    
                    # Wait for browser to persist the cookie before rerunning
                    # cookie_manager.set() is async - needs time for JS to write cookie
                    time.sleep(0.5)
                    
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")


def signup_page():
    """Display signup form."""
    st.title("🏋️ Personal Fitness Tool")
    st.subheader("Create New Account")
    
    with st.form("signup_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Sign Up")
        
        if submit:
            if not all([name, email, username, password, password_confirm]):
                st.warning("Please fill in all fields")
            elif password != password_confirm:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long")
            else:
                result = signup_user(username, email, password, name)
                if result:
                    # Auto-login after successful signup
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.cookies_loaded = True
                    
                    # Set cookie for persistent session (expires in 30 days)
                    cookie_manager.set("fitness_app_user", username, max_age=30*24*60*60, path="/")
                    
                    # Wait for browser to persist the cookie before rerunning
                    time.sleep(0.5)
                    
                    st.success("Account created successfully! Logging you in...")
                    st.rerun()
                else:
                    st.error("Username already exists. Please choose a different username.")


def auth_page():
    """Display authentication page with login and signup options."""
    # Show loading state while cookies are being retrieved
    if not st.session_state.cookies_loaded:
        with st.spinner("🔄 Checking for existing session..."):
            time.sleep(0.15)
            st.rerun()
    
    # Sidebar for navigation
    with st.sidebar:
        st.title("Navigation")
        auth_option = st.radio("Choose an option:", ["Login", "Sign Up"])
    
    if auth_option == "Login":
        login_page()
    else:
        signup_page()


def forms():
    """Display main fitness forms after authentication."""
    st.title("🏋️ Personal Fitness Tool")
    
    # Sidebar with user info and logout
    with st.sidebar:
        user = get_user(st.session_state.username)
        st.write(f"### Welcome, {user['name']}! 👋")
        st.write(f"**Username:** {st.session_state.username}")
        st.write(f"**Email:** {user['email']}")
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state FIRST before any cookie operations
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.cookies_loaded = True  # Mark as loaded to skip cookie restore
            st.session_state.rerun_count = 0
            if "profile" in st.session_state:
                del st.session_state.profile
            if "profile_id" in st.session_state:
                del st.session_state.profile_id
            if "notes" in st.session_state:
                del st.session_state.notes
            
            # Delete cookie by setting it to expire immediately (max_age=0)
            # This is more reliable than delete() which may not work properly
            cookie_manager.set("fitness_app_user", "", max_age=0, path="/")
            
            # Wait for browser to process the cookie expiry
            time.sleep(0.5)
            
            st.rerun()
    
    # Initialize profile using username as profile_id
    if "profile" not in st.session_state:
        profile_id = st.session_state.username
        profile = get_profile(profile_id)
        if not profile:
            # Create profile with user's name from auth
            profile_id, profile = create_profile(profile_id)
            # Update profile with user's actual name and save it to database
            user = get_user(st.session_state.username)
            profile = update_personal_info(
                profile,
                "general",
                name=user["name"],
                age=profile["general"]["age"],
                weight=profile["general"]["weight"],
                height=profile["general"]["height"],
                gender=profile["general"]["gender"],
                activity_level=profile["general"]["activity_level"]
            )

        st.session_state.profile = profile
        st.session_state.profile_id = profile_id

    if "notes" not in st.session_state:
        st.session_state.notes = get_notes(st.session_state.profile_id)

    # Display all forms
    personal_data_form()
    goals_form()
    macros()
    notes()
    ask_ai_func()


def main():
    """Main application entry point."""
    if st.session_state.authenticated:
        forms()
    else:
        auth_page()


if __name__ == "__main__":
    main()

# Import necessary modules and packages
from flask import Blueprint, render_template, redirect, url_for, session, request
from sqlalchemy import text
from extensions import db
from models.models import User
from sqlalchemy.exc import IntegrityError, DataError, SQLAlchemyError

# Create a blueprint for the dashboard
dashboard_bp = Blueprint('dashboard', __name__)

# Define the SQL queries for the dashboard
Queries = {
    "1": {
        "title": "View existing nominations for the user",
        "sql_statement": "SELECT * FROM USER_NOMINATION WHERE Created_by = :username"
    },
    "2": {
        "title": "View the top nominated movies by the system users in each category/year",
        "sql_statement": """
            SELECT
            U.Award_name,
            (U.iteration_number + 1928) AS Year,
            U.Movie_title,
            COUNT(U.Created_by) AS Number_of_nominations
            FROM USER_NOMINATION U
            GROUP BY U.Movie_title, U.Movie_release_date, U.Award_name, U.iteration_number
            HAVING COUNT(U.Created_by) = (
            SELECT MAX(sub.CountNominations)
            FROM (
                SELECT COUNT(*) AS CountNominations
                FROM USER_NOMINATION
                WHERE Award_name = U.Award_name AND iteration_number = U.iteration_number
                GROUP BY Movie_title, Movie_release_date
                ) sub
            );
        """
    },
    "4": {
        "title": "Show the top 5 birth countries for actors who won the best actor category",
        "sql_statement": """
            SELECT S.Country_of_birth
            FROM STAFF_MEMBER S
            JOIN NOMINATION N
            ON N.Staff_member_first_name = S.First_name AND N.Staff_member_last_name = S.Last_name
            WHERE N.Granted = 1 AND N.Award_name = 'best actor' AND S.Country_of_birth IS NOT NULL
            GROUP BY S.Country_of_birth
            ORDER BY COUNT(N.Granted) DESC
            LIMIT 5
        """
    },
    "6": {
        "title": "Dream Team - Extract the living cast members that can create the best movie ever (director who won most oscars, best leading actor, actress, supporting actor, supporting actress, producer, singer for the movie score). ",
        "sql_statement": """
            SELECT
            N.Award_name,
            N.Staff_member_first_name,
            N.Staff_member_last_name,
            COUNT(*) AS Number_of_wins
            FROM
            NOMINATION N
            JOIN STAFF_MEMBER S 
            ON N.Staff_member_first_name = S.First_name
            AND N.Staff_member_last_name = S.Last_name
            WHERE
            N.Granted = 1
            AND S.Death_date IS NULL
            GROUP BY
            N.Award_name,
            N.Staff_member_first_name,
            N.Staff_member_last_name
            ORDER BY
            N.Award_name,
            Number_of_wins DESC;
        """
    },
    "7": {
        "title": "Show the top 5 production companies by the number of won Oscars",
        "sql_statement": """
            SELECT Mp.Production_company_name AS Production_company,
            COUNT(N.Granted) AS Number_of_wins
            FROM MOVIE_PRODUCTION_COMPANY Mp
            JOIN NOMINATION N
            ON N.Movie_title = Mp.Movie_title
            AND N.Movie_release_date = Mp.Movie_release_date
            WHERE N.Granted = 1
            GROUP BY Mp.Production_company_name
            ORDER BY Number_of_wins DESC
            LIMIT 5
            """

    },
    "8": {
        "title": "List all non-english speaking movies that ever won an oscar, along with the year",
        "sql_statement": """
            SELECT DISTINCT M.title AS Movie_title, YEAR(M.release_date) AS Year
            FROM MOVIE M
            JOIN NOMINATION N
            ON N.Movie_title = M.title
            AND N.Movie_release_date = M.release_date
            WHERE N.Granted = 1
            AND M.language != 'English'
            AND M.language IS NOT NULL
        """
    },

}

# Define the routes for the dashboard
@dashboard_bp.route('/dashboard')
def dashboard():

    # Check if the user is logged in, and handle accordingly
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    # Render the dashboard template with the user and queries
    return render_template(
        'dashboard.html',
        user=User.query.filter_by(username=session['username']).first(),
        queries=Queries
    )

# Route to run a query based on the query ID
@dashboard_bp.route('/run-query', methods=['POST'])
def run_query():

    # Extract the query ID from the form data
    query_id = request.form.get('query_id')

    # Get the query information based on the query ID
    query_info = Queries.get(query_id)

    # If the query ID is not valid, return an error message
    if not query_info:
        return "Invalid query", 400

    # Execute the SQL statement associated with the query ID    
    user = User.query.filter_by(username=session['username']).first()
    result = db.session.execute(text(query_info['sql_statement']), {"username": user.username} if query_id == "1" else {})
    rows = result.fetchall()
    columns = result.keys()

    # Filter the result to get only one winner per award for query 6
    if query_id == "6":
        filtered_rows = {}
        for row in rows:
            award_name = row[0]
            if award_name not in filtered_rows:
                filtered_rows[award_name] = row
        rows = list(filtered_rows.values())


    # Render the display template with the query results
    return render_template(
        'display.html',
        title=query_info['title'],
        columns=columns,
        rows=rows,
        user=user,
    )


# Route to run a query with user input
@dashboard_bp.route('/run-query-with-input', methods=['POST'])
def run_query_with_input():

    # Get the query ID from the form data
    query_id = request.form.get('query_id')

    # Get the user from the session
    user = User.query.filter_by(username=session['username']).first()

    # First Query: Insert a nomination
    if query_id == "input_0":
    
        # Perform the insertion of a nomination using the provided form data
        success, message = insert_nomination(request.form, user)

        # Handle the success or failure of the insertion
        if success:
            return render_template("dashboard.html", success=[message], user=user, queries=Queries)
        else:
            return render_template("dashboard.html", errors=[f"Error inserting nomination: {message}"], user=user, queries=Queries)

    # Second Query: View nominations for a specific staff member
    elif query_id == "input_1":

        # Get the staff member's first and last name from the form data
        firstname = request.form.get('staff-firstname')
        lastname = request.form.get('staff-lastname')

        try:

            # Execute the SQL statement to get nominations for the specified staff member
            result = db.session.execute(text("""
                SELECT Staff_member_first_name, Staff_member_last_name, Award_name, CASE(Granted) WHEN 1 THEN 'Won' ELSE 'Nominated' END AS Status, Movie_title, Movie_release_date, Iteration_number
                FROM NOMINATION
                WHERE Staff_member_first_name = :firstname AND Staff_member_last_name = :lastname
            """), {"firstname": firstname, "lastname": lastname})

            rows = result.fetchall()
            columns = result.keys()

            # Render the display template with the query results
            return render_template(
                'display.html',
                title="Nominations for " + firstname + " " + lastname,
                columns=columns,
                rows=rows,user=user
            )
        
        except Exception as e:
            # Handle any errors that occur during the SQL execution
            db.session.rollback()
            return render_template("dashboard.html", errors=[handle_error(e)], user=user, queries=Queries)

    # Third Query: View nominations for a specific country
    elif query_id == "input_2":

        # Get the country name from the form data
        country = request.form.get('country-name')

        try:
            # Execute the SQL statement to get nominations for the specified country
            result = db.session.execute(text("""
                    SELECT S.First_name, S.Last_name, N.Award_name, COUNT(*) AS Number_of_nominations, SUM(N.Granted) AS Number_of_wins
                    FROM STAFF_MEMBER S
                    JOIN NOMINATION N
                    ON N.Staff_member_first_name = S.First_name AND N.Staff_member_last_name = S.Last_name
                    WHERE S.Country_of_birth = :country
                    GROUP BY S.First_name, S.Last_name, N.Award_name
                    ORDER BY Number_of_nominations DESC, Number_of_wins DESC
                """), {"country": country})   

            rows = result.fetchall()
            columns = result.keys()

            # Render the display template with the query results
            return render_template('display.html', title="Nominations for " + country, columns=columns, rows=rows, user=user)     
        
        except Exception as e:
            # Handle any errors that occur during the SQL execution
            db.session.rollback()
            return render_template("dashboard.html", errors=[handle_error(e)], user=user, queries=Queries)

    # render results
    return render_template("dashboard.html")


def handle_error(e):
    if isinstance(e, IntegrityError):
        msg = str(e.orig).lower()
        if "duplicate" in msg:
            return "A nomination with the same data already exists."
        elif "foreign key" in msg:
            return "You tried to insert a reference that does not exist (e.g., movie or staff not found)."
        elif "null value" in msg:
            return "One of the required fields was missing."
        else:
            return "Integrity constraint failed."
    elif isinstance(e, DataError):
        return "The data you entered is invalid or too long."
    elif isinstance(e, SQLAlchemyError):
        return "Database error occurred."
    else:
        return "An unknown error occurred."
    
def insert_nomination(form, user):

    # Check if an input is missing
    for input in form:
        if not form.get(input):
            return False, f"Missing input: {input}"

    # Map the form data to a dictionary
    data = {
        "title": form.get('movie-title'),
        "release_date": form.get('movie-release-date'),
        "award": form.get('award-name'),
        "firstname": form.get('staff-firstname'),
        "lastname": form.get('staff-lastname'),
        "iteration": form.get('iteration-number')
    }

    try:

        # Perform the insertion of a nomination using the provided data
        db.session.execute(text(
            "INSERT INTO USER_NOMINATION "
            "VALUES (:title, :release_date, :firstnamem, :lastname, :iteration_number, :award_name, :created_by)"
        ), {
            "title": data['title'].capitalize(),
            "release_date": data['release_date'],
            "firstnamem": data['firstname'].capitalize(),
            "lastname": data['lastname'].capitalize(),
            "iteration_number": data['iteration'],
            "award_name": data['award'].lower(),
            "created_by": user.username
        })

        db.session.commit()
        return True, "Nomination inserted successfully."

    except Exception as e:
        # Handle any errors that occur during the SQL execution
        db.session.rollback()
        return False, handle_error(e)
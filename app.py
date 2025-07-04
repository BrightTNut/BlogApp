from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, jsonify
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# ✅ MySQL Configuration
app.config["MYSQL_HOST"] = "database-1.cbacqumaoopg.eu-north-1.rds.amazonaws.com"
app.config["MYSQL_USER"] = "admin"
app.config["MYSQL_PASSWORD"] = "Pass100123"
app.config["MYSQL_DB"] = "flask"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# ✅ Initialize MySQL
mysql = MySQL(app)

# ✅ Secret Key for Sessions
app.secret_key = "secret123"

# ✅ Home Route
@app.route("/")
def index():
    return render_template("home.html")


# ✅ About Page
@app.route("/about")
def about():
    return render_template("about.html")


# ✅ Fetch All Articles
@app.route("/articles")
def articles():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()
    cur.close()

    if result > 0:
        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html", msg="No Articles Found")


# ✅ Fetch Single Article
@app.route("/article/<string:id>/")
def article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()
    cur.close()

    if article:
        return render_template("article.html", article=article)
    else:
        flash("Article not found", "danger")
        return redirect(url_for("articles"))


# ✅ Register Form
class RegisterForm(Form):
    name = StringField("Name", [validators.Length(min=1, max=50)])
    username = StringField("Username", [validators.Length(min=4, max=25)])
    email = StringField("Email", [validators.Length(min=6, max=50)])
    password = PasswordField("Password", [
        validators.DataRequired(),
        validators.EqualTo("confirm", message="Passwords do not match"),
    ])
    confirm = PasswordField("Confirm Password")


# ✅ User Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
            (name, email, username, password),
        )
        mysql.connection.commit()
        cur.close()

        flash("You are now registered and can log in", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


# ✅ User Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password_candidate = request.form["password"]

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            stored_password = data["password"]
            cur.close()

            if sha256_crypt.verify(password_candidate, stored_password):
                session["logged_in"] = True
                session["username"] = username

                flash("You are now logged in", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid login credentials", "danger")
                return render_template("login.html")

        flash("Username not found", "danger")
        return render_template("login.html")

    return render_template("login.html")


# ✅ Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for("login"))


# ✅ Authentication Decorator
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized! Please login", "danger")
            return redirect(url_for("login"))

    return wrap


# ✅ Dashboard (Requires Login)
@app.route("/dashboard")
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE author = %s", [session["username"]])
    articles = cur.fetchall()
    cur.close()

    if result > 0:
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html", msg="No Articles Found")


# ✅ Article Form
class ArticleForm(Form):
    title = StringField("Title", [validators.Length(min=1, max=200)])
    body = TextAreaField("Body", [validators.Length(min=30)])


# ✅ Add Article
@app.route("/add_article", methods=["GET", "POST"])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session["username"]))
        mysql.connection.commit()
        cur.close()

        flash("Article Created", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_article.html", form=form)


# ✅ Edit Article
@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()
    cur.close()

    if not article:
        flash("Article not found", "danger")
        return redirect(url_for("dashboard"))

    form = ArticleForm(request.form)
    form.title.data = article["title"]
    form.body.data = article["body"]

    if request.method == "POST" and form.validate():
        title = request.form["title"]
        body = request.form["body"]

        cur = mysql.connection.cursor()
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))
        mysql.connection.commit()
        cur.close()

        flash("Article Updated", "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_article.html", form=form)


# ✅ Delete Article
@app.route("/delete_article/<string:id>", methods=["POST"])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()

    flash("Article Deleted", "success")
    return redirect(url_for("dashboard"))


# ✅ Run Flask App
if __name__ == "__main__":
    app.run(debug=True)

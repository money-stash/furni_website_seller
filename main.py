from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "Lql8aLsBzUVWvY6Ood1egDyanmTwN2GV"  # обязательно для сессий

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/shop")
def shop():
    return render_template("shop.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            flash("Неправильный логин или пароль", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin-login.html")


@app.route("/admin-panel")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    return render_template("admin-panel.html")


@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)

    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    app.run(debug=True)

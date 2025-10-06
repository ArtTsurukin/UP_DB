from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy


from models import User, Part, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///updb.db"


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/parts", methods=["GET"])
def all_parts():
    return "all parts"

@app.route("/parts/new_part", methods=["GET"])
def new_part_form():
    return render_template("new_part.html")

@app.route("/parts/<int:pid>", methods=["GET"])
def get_one_part(pid):
    try:
        part = db.session.get(Part, pid)
        return f"{part.name}"
    except Exception as e:
        return f"error - {e}"

@app.route("/parts/<int:pid>", methods=["DELETE"])
def delete_one_part(pid):
    try:
        to_delete = db.session.get(Part, pid)
        db.session.delete(to_delete)
        db.session.commit()
        return "deleted"
    except Exception as e:
        return f"error - {e}"

@app.route("/parts/new_part/added", methods=["POST"])
def add_new_part():
    try:
        part = Part(
            name=request.form['name'],
            part_number=request.form['part_number'],
            description=request.form.get('description', ''),
            price_in=int(request.form['price_in']),
            price_out=int(request.form['price_out'])
        )
        db.session.add(part)
        db.session.commit()
        return redirect('/parts')
    except (KeyError, ValueError) as e:
        return f"Ошибка в данных: {str(e)}", 400


if __name__ == "__main__":
    with app.app_context():
        db.init_app(app)
        db.create_all()
    app.run()
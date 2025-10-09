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
    parts = Part.query.all()
    return render_template("all_parts.html" , parts=parts)

@app.route("/parts/new_part", methods=["GET"])
def new_part_form():
    return render_template("new_part.html")

@app.route("/parts/<int:pid>", methods=["GET"])
def get_one_part(pid):
    try:
        part = db.session.get(Part, pid)
        return render_template("part.html", part=part)
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


@app.route("/parts/<int:pid>/edit", methods=["GET", "POST"])
def edit_part(pid):
    part = Part.query.get_or_404(pid)

    if request.method == "POST":
        try:
            # Обновляем все поля кроме id
            part.name = request.form['name']
            part.part_number = request.form['part_number']
            part.description = request.form['description']
            part.price_in = int(request.form['price_in'])
            part.price_out = int(request.form['price_out'])

            db.session.commit()
            return redirect(f"/parts/{pid}")
        except Exception as e:
            return f"Ошибка при обновлении: {str(e)}", 400

    # GET запрос - показываем форму редактирования
    return render_template('edit_part.html', part=part)


if __name__ == "__main__":
    with app.app_context():
        db.init_app(app)
        db.create_all()
    app.run()
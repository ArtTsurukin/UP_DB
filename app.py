from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/add_part")
def add_part():
    return render_template("add_part.html")



if __name__ == '__main__':
    app.run()
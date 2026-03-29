from flask import Flask, render_template, request, redirect, session, abort
import sqlite3, os

app = Flask(__name__)
app.secret_key = "ndalu_secret"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect("ndalustore.db")
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        image TEXT,
        file TEXT,
        video TEXT,
        download_count INTEGER DEFAULT 0
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        username TEXT,
        comment TEXT
    )
    """)
    return conn

# ---------- HOME ----------
@app.route("/")
def home():
    conn = get_db()
    games = conn.execute("SELECT * FROM games ORDER BY download_count DESC").fetchall()
    conn.close()
    return render_template("home.html", games=games)

# ---------- GAME PAGE ----------
@app.route("/game/<int:id>", methods=["GET","POST"])
def game_page(id):
    conn = get_db()
    game = conn.execute("SELECT * FROM games WHERE id=?", (id,)).fetchone()
    if not game:
        conn.close()
        return "Game not found",404

    if request.method=="POST":
        username = request.form["username"]
        comment = request.form["comment"]
        conn.execute("INSERT INTO comments (game_id, username, comment) VALUES (?,?,?)", (id, username, comment))
        conn.commit()

    comments = conn.execute("SELECT * FROM comments WHERE game_id=? ORDER BY id DESC",(id,)).fetchall()
    conn.close()
    return render_template("game.html", game=game, comments=comments)

# ---------- DOWNLOAD ----------
@app.route("/go/<int:id>")
def go(id):
    conn = get_db()
    game = conn.execute("SELECT * FROM games WHERE id=?", (id,)).fetchone()
    if game:
        conn.execute("UPDATE games SET download_count = download_count + 1 WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return redirect(game["file"])  # or your AdFly link
    conn.close()
    abort(404)

# ---------- ADMIN LOGIN ----------
ADMIN_USER = "ndalustore"
ADMIN_PASS = "WANTED2025"

@app.route("/ndalustore_admin_hidden", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form["username"]==ADMIN_USER and request.form["password"]==ADMIN_PASS:
            session["admin"]=True
            return redirect("/dashboard")
        else:
            return "Wrong login"
    return render_template("admin_login.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if not session.get("admin"): abort(404)
    conn = get_db()

    # UPLOAD GAME
    if request.method=="POST" and "upload" in request.form:
        name = request.form["name"]
        category = request.form["category"]
        video = request.form.get("video","")

        image_file = request.files["image"]
        game_file = request.files["gamefile"]
        image_name = image_file.filename
        game_name = game_file.filename
        image_file.save(os.path.join(UPLOAD_FOLDER, image_name))
        game_file.save(os.path.join(UPLOAD_FOLDER, game_name))
        file_link = f"/static/uploads/{game_name}"

        conn.execute("INSERT INTO games (name, category, image, file, video) VALUES (?,?,?,?,?)",
                     (name, category, image_name, file_link, video))
        conn.commit()
        return redirect("/dashboard")

    # DELETE GAME
    if request.method=="POST" and "delete_id" in request.form:
        delete_id = request.form["delete_id"]
        game = conn.execute("SELECT * FROM games WHERE id=?", (delete_id,)).fetchone()
        if game:
            try:
                if game["image"]: os.remove(os.path.join(UPLOAD_FOLDER, game["image"]))
                if game["file"]: os.remove(os.path.join(UPLOAD_FOLDER, os.path.basename(game["file"])))
            except:
                pass
            conn.execute("DELETE FROM games WHERE id=?", (delete_id,))
            conn.execute("DELETE FROM comments WHERE game_id=?", (delete_id,))
            conn.commit()
        return redirect("/dashboard")

    games = conn.execute("SELECT * FROM games ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("dashboard.html", games=games)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/ndalustore_admin_hidden")

# ---------- RUN (Render Ready) ----------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
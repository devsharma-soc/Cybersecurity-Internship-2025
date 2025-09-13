from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import os
import sfi_core

app = Flask(__name__)
app.secret_key = "supersecret"  # needed for flash messages

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        cover = request.files.get("cover")
        target = request.files.get("target")

        if not cover:
            flash("Cover file is required!")
            return redirect(url_for("index"))

        # save cover file
        cover_path = os.path.join(UPLOAD_FOLDER, cover.filename)
        cover.save(cover_path)

        target_path = None
        if target and target.filename:
            target_path = os.path.join(UPLOAD_FOLDER, target.filename)
            target.save(target_path)

        try:
            if action == "embed":
                if not target_path:
                    flash("Target file required for embedding!")
                    return redirect(url_for("index"))
                out_path = os.path.join(OUTPUT_FOLDER, "stego.wav")
                sfi_core.embed_audio(cover_path, out_path, [target_path])
                return send_file(out_path, as_attachment=True)

            elif action == "extract":
                out_path = os.path.join(OUTPUT_FOLDER, "manifest.json")
                manifest = sfi_core.extract(cover_path, out_path)
                return send_file(out_path, as_attachment=True)

            elif action == "verify":
                if not target_path:
                    flash("Target file required for verification!")
                    return redirect(url_for("index"))
                results = sfi_core.verify(cover_path, [target_path])
                return render_template("result.html", results=results)

            else:
                flash("Invalid action selected!")
                return redirect(url_for("index"))

        except Exception as e:
            flash(f"Error: {str(e)}")
            return redirect(url_for("index"))

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

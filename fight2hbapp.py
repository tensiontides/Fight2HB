import os
import sys
from flask import Flask, render_template, request, session
from werkzeug.utils import secure_filename
import tempfile
from argparse import Namespace

import parse as ps 

app = Flask(__name__)
app.secret_key = os.urandom(24)

# max upload 5 mbs
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


def get_tmpfile_path():
    return os.path.join(tempfile.gettempdir(), "tmp.xml")




@app.route("/", methods=['GET','POST'])
def index():
    session["FINISHED"] = False
    session["LOADED"] = False
    file_content = [""]
    if request.method == 'POST':
        # print(request.form.__dict__)
        if request.form['submitupload'] == "Convert!" :
            # for secure filenames. Read the documentation.
            file = request.files['myfile']
            filename = secure_filename(file.filename)
            tmpdir = tempfile.gettempdir()
            # print(tmpdir)
            # tmpfile = os.path.join(tmpdir, filename)
            tmpfile = get_tmpfile_path()
            file.save(tmpfile)
            with open(tmpfile) as f:
                try :
                    file_content = f.read().split("\n")
                except Exception as e:
                    print(e)
                    results = "Unable to read file." + e
                    profile = ""
            teaser = "\n".join(file_content[0:7])
            addn_lines = len(file_content) - 7
            if addn_lines < 0:
                addn_lines = 0
            header = "Here is the first bit of your file:"
            session["LOADED"] = True

            ###   Now lets run the main function
            if os.path.isfile(tmpfile):
                results, spells_dict  = runconverter(
                    infile=tmpfile
                )
            else:
                results = "Unable to read file.  Are you sure its a valid Fight Club XML?"
                profile = ""
            ###
            return render_template(
                'index.html',
                version="0.0.0",
                header=header,
                content=teaser,
                results=results,
                spells="\n\n".join([v[1] for k, v in spells_dict.items()]),
                nlines="...and %d more lines" % addn_lines
            )
        else:
            pass
    else:
        return render_template(
            "index.html",
            version="0.0.0")

def runconverter(infile):
    # prepare args
    args = Namespace(infile=infile,
                     compendium="Complete.xml",
                     spells=True)
    spell_dict = {}
    try:
        pc, spell_dict  = ps.main(args)
    except Exception as e:
        if e is ImportError:
            pc = "Deploy error!"
        else:
            print(e)
            pc = str("Error!")
    return (pc, spell_dict)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")

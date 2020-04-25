from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import make_response
from uuid import uuid1
import pymysql
import math

app = Flask(__name__, static_folder="static", template_folder="templates")

def getConnection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        passwd='123',
        db='dcinside')
    return connection

@app.route("/")
def main():
    return render_template("main.html")

#회원가입 로그인-----------------------------------------------------------------------------------------------------------------------

@app.route("/join")
def join():
    return render_template("join.html")

@app.route("/join_process", methods=['POST'])
def join_process():
    user_id = request.form.get("user_id")
    user_pw = request.form.get("user_pw")
    user_name = request.form.get("user_name")
    uuid = str(uuid1())

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "INSERT INTO members(user_id, user_pw, user_name, uuid) VALUES (%s, %s, %s, %s)"
    cursor.execute(sql, (user_id, user_pw, user_name, uuid))

    connection.commit()
    connection.close()

    response = make_response(redirect("/welcome"))
    response.set_cookie("uuid", uuid)

    return response

@app.route("/welcome")
def welcome():
    uuid = request.cookies.get("uuid")

    if uuid == None:
        return redirect("/error")
    
    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM members WHERE uuid=%s"
    cursor.execute(sql,(uuid))

    row = cursor.fetchone()
    connection.close()

    if row == None:
        return redirect("/warning")
    else:
        return render_template("welcome.html", member = row)

@app.route("/error")
def error():
    return render_template("error.html")

@app.route("/warning")
def warning():
    return render_template("warning.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login_process", methods=['POST'])
def login_process():
    user_id = request.form.get("user_id")
    user_pw = request.form.get("user_pw")

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM members WHERE user_id=%s"
    cursor.execute(sql, (user_id))

    row = cursor.fetchone()
    connection.close()

    if row == None:
        return redirect("/wrong")
    
    if row['user_pw'] == user_pw:
        connection = getConnection()
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        uuid = str(uuid1())
        response = make_response(redirect("/welcome"))
        response.set_cookie("uuid", uuid)

        sql = "UPDATE members SET uuid=%s WHERE user_id=%s"
        cursor.execute(sql, (uuid, user_id))

        connection.commit()
        connection.close()

        return response
    else:
        return redirect("/wrong")

@app.route("/wrong")
def wrong():
    return render_template("wrong.html")

#글쓰기, 게시판(페이지네이션), 글수정, 삭제-------------------------------------------------------------------------------------------------

@app.route("/write")
def write():
    uuid = request.cookies.get("uuid")

    if uuid == None:
        return redirect("/error")
    
    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM members WHERE uuid=%s"
    cursor.execute(sql,(uuid))

    row = cursor.fetchone()
    connection.close()

    if row == None:
        return redirect("/warning")
    else:
        return render_template("write.html")

@app.route("/write_process", methods=['POST'])
def write_process():
    uuid = request.cookies.get("uuid")
    title = request.form.get("title")
    content = request.form.get("content")

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM members WHERE uuid=%s"
    cursor.execute(sql, (uuid))
    row = cursor.fetchone()

    sql = "INSERT INTO boards(title, content, member_id) VALUES (%s, %s, %s)"
    cursor.execute(sql, (title, content, row['id']))

    connection.commit()
    connection.close()

    return redirect("/boards")

@app.route("/boards", methods=['GET'])
def boards():
    page = request.args.get("page")
    if page == None:
        page = 1
    else:
        page = int(page)

    connection=getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT boards.id, boards.title, boards.content, members.user_name FROM boards JOIN members ON boards.member_id = members.id ORDER BY boards.id DESC LIMIT %s,10"
    cursor.execute(sql,((page-1)*10))
    rows = cursor.fetchall()
    
    sql = "SELECT COUNT(*) AS count FROM boards"
    cursor.execute(sql)
    result = cursor.fetchone()

    boardCount = result['count']
    pageCount = math.ceil(boardCount / 10)

    pages=[]
    for i in range(1, pageCount +1):
        pages.append(i)
    return render_template("boards.html", boards=rows, pages=pages)

@app.route("/detail", methods=['GET'])
def detail():
    detail_id = request.args.get("detail_id")

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    #detail에 보여줄 게시글번호, 제목, 내용, 글쓴이, 
    sql = "SELECT boards.id, boards.title, boards.content, members.user_name FROM boards JOIN members ON boards.member_id = members.id WHERE boards.id=%s"
    cursor.execute(sql, (detail_id))
    row = cursor.fetchone()
    #detail에 보여줄 댓글 > 댓글내용, 댓글쓴이
    sql = "SELECT comments.content, members.user_name FROM comments JOIN members ON comments.member_id = members.id WHERE comments.board_id = %s"    
    cursor.execute(sql, (detail_id))
    comments = cursor.fetchall()

    connection.close()
    
    return render_template("detail.html", detail=row, comments=comments)

@app.route("/detail/comment", methods=["POST", "GET"])
def addComment():
    uuid = request.cookies.get("uuid")

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM members WHERE uuid=%s"
    cursor.execute(sql, (uuid))
    row = cursor.fetchone()
    
    board_id = request.args.get("id")
    content = request.form.get("content")
    
    sql = "INSERT INTO comments(content, board_id, member_id) VALUES(%s, %s, %s)"
    cursor.execute(sql, (content, board_id, row['id']))

    connection.commit()
    connection.close()

    return redirect("/detail?detail_id=" + board_id)

@app.route("/delete", methods=['GET'])
def delete():
    delete_id = request.args.get("delete_id")
    uuid = request.cookies.get("uuid")

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM boards WHERE id=%s"
    cursor.execute(sql,(delete_id))
    board_row = cursor.fetchone()

    sql = "SELECT * FROM members WHERE uuid=%s"
    cursor.execute(sql,(uuid))
    member_row = cursor.fetchone()

    connection.close()

    if board_row["member_id"] == member_row["id"]:
        connection = getConnection()
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        sql = "DELETE FROM boards WHERE id = %s"
        cursor.execute(sql, (delete_id)) 

        connection.commit()
        connection.close()

        return redirect("/alert")
    else:
        return "사용자만 삭제할 수 있습니다."

@app.route("/alert")
def alert():
    return render_template("alert.html")

@app.route("/edit", methods=['GET','POST'])
def edit():
    uuid = request.cookies.get("uuid")
    edit = request.form.get("edit")
    board_id = request.args.get("edit_id")

    if uuid == None:
        return "로그인이 되어있지 않습니다."

    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM members WHERE uuid=%s"
    cursor.execute(sql,(uuid))

    member = cursor.fetchone()
    connection.close()

    if member == None:
        return redirect("/warning")
    
    connection = getConnection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT * FROM boards WHERE id=%s"
    cursor.execute(sql,(board_id))
    board = cursor.fetchone()

    connection.close()

    if member['id'] == board['member_id']:
        connection = getConnection()
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        sql = "UPDATE boards SET content = %s WHERE id = %s"
        cursor.execute(sql, (edit, board_id))

        connection.commit()
        connection.close()

        return redirect("/detail?detail_id="+board_id)
    else:
        return "작성자만 수정할 수 있습니다."

app.run(port=3005, debug=True)
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS

app = Flask(__name__)  # Corrected from _name_

CORS(app)

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'super_market'

mysql = MySQL(app)

# Route to get item position from rack
@app.route("/get_item_position", methods=["POST"])
def get_item_position():
    _json = request.json
    item_name = _json.get('item_name')

    cursor = mysql.connection.cursor()
    query = """
        SELECT i.item_name, rp.row_from_top, rp.position_in_row 
        FROM Items i
        JOIN Rack_Positions rp ON i.item_id = rp.item_id 
        WHERE i.item_name = %s
    """
    cursor.execute(query, (item_name,))
    result = cursor.fetchone()

    if result:
        response = {
            'item_name': result[0],
            'row_from_top': result[1],
            'position_in_row': result[2]
        }
        cursor.close()
        return jsonify(response)
    else:
        cursor.close()
        return jsonify({"error": "Item not found"}), 404

# Run app
if __name__ == "__main__":
    app.run(debug=True,threaded=True)

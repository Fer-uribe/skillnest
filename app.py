from flask import Flask, render_template, redirect, request, session, url_for, flash, make_response, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__, template_folder='templates')

# Configuración de MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '62238009'
app.config['MYSQL_DB'] = 'skillnest'

mysql = MySQL(app)
app.secret_key = 'fernando'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/registro', methods=['POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username']
        lastname = request.form['lastname']
        email_reg = request.form['email_reg']
        password_reg = request.form['password_reg']

        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO usuarios (nombre, apellido, email, password) VALUES (%s, %s, %s, %s)',
                    (username, lastname, email_reg, password_reg))
        mysql.connection.commit()
        cur.close()

        flash('Usuario registrado con éxito, ahora inicia sesión', 'success')
        return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email_log = request.form['email_log']
        password_log = request.form['password_log']

        cur = mysql.connection.cursor()
        cur.execute('SELECT idusuarios, nombre, apellido, email, password FROM usuarios WHERE email = %s AND password = %s', (email_log, password_log))
        user = cur.fetchone()
        cur.close()

        if user:
            session['id_user'] = user[0]
            session['nombre_user'] = user[1]
            session['apellido_user'] = user[2]
            session['email_user'] = user[3]
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')
            return redirect(url_for('home'))

@app.context_processor
def inject_user():
    return dict(session=session)

@app.route('/dashboard')
def dashboard():
    if 'id_user' not in session:
        flash('Debes iniciar sesión primero', 'warning')
        return redirect(url_for('home'))
    id_usuario = session['id_user']

    cur = mysql.connection.cursor()
    cur.execute('SELECT idvisita, parque, fecha, rating, detalles, `like` FROM visita WHERE iduser = %s', (session['id_user'],))
    user_visits = cur.fetchall()

    cur.execute('''
        SELECT v.idvisita, v.parque, v.fecha, v.rating, v.detalles, v.iduser, v.`like`, u.nombre 
        FROM visita v 
        JOIN usuarios u ON v.iduser = u.idusuarios 
        WHERE v.iduser != %s 
        ORDER BY v.rating DESC
    ''', (id_usuario,))
    other_user_visits = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', my_visits=user_visits, all_visits=other_user_visits)

@app.route('/reg_visita', methods=['POST'])
def reg_visita():
    if 'id_user' not in session:
        flash('Debes iniciar sesión primero', 'warning')
        return redirect(url_for('home'))

    if request.method == 'POST':
        parque = request.form['parque']
        fecha_visita = request.form['fecha_visita']
        rating = request.form['rating']
        detalles = request.form['detalles']

        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO visita (parque, fecha, rating, detalles, iduser) VALUES (%s, %s, %s, %s, %s)',
                    (parque, fecha_visita, rating, detalles, session['id_user']))
        mysql.connection.commit()
        cur.close()

        flash('Visita agregada correctamente', 'success')
        return redirect(url_for('dashboard'))

@app.route('/nueva')
def nueva():
    if 'id_user' not in session:
        flash('Debes iniciar sesión primero', 'warning')
        return redirect(url_for('home'))

    return render_template('nueva.html')

@app.route('/actualizar_visita/<int:id_visita>', methods=['POST'])
def actualizar_visita(id_visita):
    if 'id_user' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        parque = request.form['parque']
        fecha_visita = request.form['fecha_visita']
        rating = request.form['rating']
        detalles = request.form['detalles']
        
        cur = mysql.connection.cursor()
        cur.execute('''
            UPDATE visita 
            SET parque = %s, fecha = %s, rating = %s, detalles = %s 
            WHERE idvisita = %s AND iduser = %s
        ''', (parque, fecha_visita, rating, detalles, id_visita, session['id_user']))
        mysql.connection.commit()
        cur.close()
        
        flash('Visita actualizada correctamente')
        return redirect(url_for('dashboard'))

@app.route('/editar/<int:id_visita>')
def editar(id_visita):
    if 'id_user' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute('SELECT parque, fecha, rating, detalles FROM visita WHERE idvisita = %s AND iduser = %s', 
                (id_visita, session['id_user']))
    visita = cur.fetchone()
    
    if not visita:
        flash('No tienes permiso para editar esta visita o no existe')
        return redirect(url_for('dashboard'))

    return render_template('editar.html', visita=visita, id_visita=id_visita)

@app.route('/eliminar/<int:id_visita>', methods=['POST'])
def eliminar(id_visita):
    if 'id_user' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM visita WHERE idvisita = %s AND iduser = %s', 
                (id_visita, session['id_user']))
    mysql.connection.commit()
    cur.close()

    flash('Visita eliminada correctamente')
    return redirect(url_for('dashboard'))


@app.route('/ver/<int:id_visita>')
def ver(id_visita):
    if 'id_user' not in session:
        return redirect(url_for('home'))
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT parque, fecha, rating, detalles FROM visita WHERE idvisita = %s', (id_visita,))
    visita = cur.fetchone()

    return render_template('ver.html', visita=visita, id_visita=id_visita)

@app.route('/like/<int:id_visita>', methods=['POST'])
def like_visita(id_visita):
    if 'id_user' not in session:
        return redirect(url_for('home'))

    if 'liked_visitas' not in session:
        session['liked_visitas'] = []

    if id_visita in session['liked_visitas']:
        return redirect(url_for('ver', id_visita=id_visita))

    try:
        cur = mysql.connection.cursor()
        cur.execute('UPDATE visita SET `like` = `like` + 1 WHERE idvisita = %s', (id_visita,))
        mysql.connection.commit()

        session['liked_visitas'].append(id_visita)

        return redirect(url_for('ver', id_visita=id_visita))

    except mysql.connector.Error as err:
        print(f"Error de MySQL: {err}")
        return redirect(url_for('ver', id_visita=id_visita))

    finally:
        if 'cur' in locals() and cur:
            cur.close()



@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
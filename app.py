import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from google import genai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_123'

# Render'dagi PostgreSQL bazasini avtomatik aniqlash va ulash
db_url = os.environ.get('DATABASE_URL', 'sqlite:///pharmacy.db')

if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Gemini AI sozlamasi
client = genai.Client(api_key="AQ.Ab8RN6LN7UEtSwLHekxRniGN2YBWmuSTBef14CYh-r_BD8QY8A")


def get_ai_medicine_advice(medicine_name):
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Qisqacha o'zbek tilida ma'lumot bering: '{medicine_name}' dorisi nima uchun ishlatiladi va qanday qabul qilinadi?",
        )
        return response.text
    except Exception as e:
        print("AI XATOLIK SABABI:", e)
        return "AI ma'lumot bera olmadi."


# Dori modeli (Baza strukturasi)
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiration_date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)


# Jadvallarni avtomatik yaratish
with app.app_context():
    db.create_all()


# Bosh sahifa - Dorilar ro'yxati
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    if search_query:
        medicines = Medicine.query.filter(Medicine.name.icontains(search_query)).all()
    else:
        medicines = Medicine.query.all()
    return render_template('index.html', medicines=medicines, search_query=search_query)


# Dorini sotish (sonini 1 taga kamaytirish)
@app.route('/sell/<int:id>')
def sell_medicine(id):
    med = Medicine.query.get_or_404(id)
    if med.quantity > 0:
        med.quantity -= 1
        db.session.commit()
        flash(f"{med.name} muvaffaqiyatli sotildi!", "success")
    else:
        flash(f"{med.name} omborda qolmagan!", "danger")
    return redirect(url_for('index'))


# Yangi dori qo'shish (AI integratsiyasi bilan)
@app.route('/add', methods=['GET', 'POST'])
def add_medicine():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        expiration_date = request.form['expiration_date']
        description = request.form['description']

        if not description:
            description = get_ai_medicine_advice(name)

        new_med = Medicine(
            name=name,
            category=category,
            price=price,
            quantity=quantity,
            expiration_date=expiration_date,
            description=description
        )
        db.session.add(new_med)
        db.session.commit()
        flash("Dori AI yordamida muvaffaqiyatli qo'shildi!", "success")
        return redirect(url_for('index'))

    return render_template('add_medicine.html')


# Dorini tahrirlash
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_medicine(id):
    med = Medicine.query.get_or_404(id)
    if request.method == 'POST':
        med.name = request.form['name']
        med.category = request.form['category']
        med.price = float(request.form['price'])
        med.quantity = int(request.form['quantity'])
        med.expiration_date = request.form['expiration_date']
        med.description = request.form['description']

        db.session.commit()
        flash("Dori ma'lumotlari yangilandi!", "info")
        return redirect(url_for('index'))

    return render_template('edit_medicine.html', med=med)


# Dorini o'chirish
@app.route('/delete/<int:id>')
def delete_medicine(id):
    med = Medicine.query.get_or_404(id)
    db.session.delete(med)
    db.session.commit()
    flash("Dori tizimdan o'chirildi!", "danger")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Inicializar Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambiala-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///erp_consultora.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# MODELOS DE BASE DE DATOS
# -------------------------

class Usuario(UserMixin, db.Model):
    """Modelo para empleados/consultores"""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(50), default='consultor')  # admin, consultor, gerente
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    proyectos_asignados = db.relationship('Proyecto', backref='responsable', lazy=True)
    facturas_emitidas = db.relationship('Factura', backref='creador', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Cliente(db.Model):
    """Modelo para empresas clientes"""
    id = db.Column(db.Integer, primary_key=True)
    nombre_empresa = db.Column(db.String(200), nullable=False)
    contacto = db.Column(db.String(100))
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    proyectos = db.relationship('Proyecto', backref='cliente', lazy=True)

class Proyecto(db.Model):
    """Modelo para servicios/consultorías"""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_entrega = db.Column(db.DateTime)
    estado = db.Column(db.String(50), default='activo')  # activo, completado, pausado
    presupuesto = db.Column(db.Float, default=0)
    
    # Relaciones
    facturas = db.relationship('Factura', backref='proyecto', lazy=True)

class Factura(db.Model):
    """Modelo para facturación"""
    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), unique=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime)
    pagada = db.Column(db.Boolean, default=False)
    metodo_pago = db.Column(db.String(50))
    
class DetalleFactura(db.Model):
    """Modelo para líneas de detalle de cada factura"""
    __tablename__ = 'detalle_factura'
    
    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, db.ForeignKey('factura.id'), nullable=False)
    concepto = db.Column(db.String(200), nullable=False)  # Descripción del servicio
    cantidad = db.Column(db.Integer, default=1)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)  # cantidad * precio_unitario
    
    # Relación con Factura (acceso desde factura.detalles)
    factura = db.relationship('Factura', backref=db.backref('detalles', lazy=True, cascade='all, delete-orphan'))
    
    @staticmethod
    def calcular_subtotal(cantidad, precio_unitario):
        return cantidad * precio_unitario

# Crear tablas (ejecutar una vez)
with app.app_context():
    db.create_all()
    # Crear admin si no existe
    if not Usuario.query.filter_by(email='admin@consultora.com').first():
        admin = Usuario(
            nombre='Administrador',
            email='admin@consultora.com',
            rol='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# RUTAS DE AUTENTICACIÓN
# -----------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.check_password(password):
            login_user(usuario)
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# RUTAS PRINCIPALES
# -----------------

@app.route('/')
@login_required
def dashboard():
    # ============================================
    # 1. ESTADÍSTICAS BÁSICAS (las que ya tenías)
    # ============================================
    total_clientes = Cliente.query.count()
    total_proyectos = Proyecto.query.count()
    proyectos_activos = Proyecto.query.filter_by(estado='activo').count()
    total_facturas = Factura.query.count()
    facturas_pendientes = Factura.query.filter_by(pagada=False).count()
    facturas_pagadas = Factura.query.filter_by(pagada=True).count()
    
    # ============================================
    # 2. DATOS PARA GRÁFICOS
    # ============================================
    
    # 2.1 Facturación por mes (últimos 6 meses)
    from datetime import datetime, timedelta
    import calendar
    
    meses = []
    montos_mensuales = []
    facturas_mensuales = []
    
    for i in range(5, -1, -1):
        fecha = datetime.now() - timedelta(days=30*i)
        mes = fecha.month
        año = fecha.year
        nombre_mes = calendar.month_name[mes][:3] + f" {año}"
        meses.append(nombre_mes)
        
        # Facturas del mes
        facturas_mes = Factura.query.filter(
            db.extract('year', Factura.fecha_emision) == año,
            db.extract('month', Factura.fecha_emision) == mes
        ).all()
        
        monto_total = sum(f.monto for f in facturas_mes)
        montos_mensuales.append(float(monto_total))
        facturas_mensuales.append(len(facturas_mes))
    
    # 2.2 Facturación por cliente (top 5)
    clientes_top = db.session.query(
        Cliente.nombre_empresa,
        db.func.sum(Factura.monto).label('total_facturado')
    ).join(Proyecto, Proyecto.cliente_id == Cliente.id)\
     .join(Factura, Factura.proyecto_id == Proyecto.id)\
     .group_by(Cliente.id)\
     .order_by(db.func.sum(Factura.monto).desc())\
     .limit(5).all()
    
    nombres_clientes = [c[0] for c in clientes_top]
    montos_clientes = [float(c[1]) for c in clientes_top]
    
    # 2.3 Proyectos por estado
    proyectos_por_estado = db.session.query(
        Proyecto.estado,
        db.func.count(Proyecto.id).label('total')
    ).group_by(Proyecto.estado).all()
    
    estados_proyecto = [p[0].capitalize() for p in proyectos_por_estado]
    cantidades_proyecto = [p[1] for p in proyectos_por_estado]
    
    # 2.4 Facturas pagadas vs pendientes (últimos 30 días)
    fecha_limite = datetime.now() - timedelta(days=30)
    facturas_recientes = Factura.query.filter(Factura.fecha_emision >= fecha_limite).all()
    
    pagadas_recientes = sum(1 for f in facturas_recientes if f.pagada)
    pendientes_recientes = len(facturas_recientes) - pagadas_recientes
    monto_pagado_reciente = sum(f.monto for f in facturas_recientes if f.pagada)
    monto_pendiente_reciente = sum(f.monto for f in facturas_recientes if not f.pagada)
    
    # ============================================
    # 3. PROYECTOS RECIENTES (igual que antes)
    # ============================================
    proyectos_recientes = Proyecto.query.order_by(Proyecto.fecha_inicio.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         # Estadísticas básicas
                         total_clientes=total_clientes,
                         total_proyectos=total_proyectos,
                         proyectos_activos=proyectos_activos,
                         total_facturas=total_facturas,
                         facturas_pendientes=facturas_pendientes,
                         facturas_pagadas=facturas_pagadas,
                         
                         # Datos para gráficos
                         meses=meses,
                         montos_mensuales=montos_mensuales,
                         facturas_mensuales=facturas_mensuales,
                         nombres_clientes=nombres_clientes,
                         montos_clientes=montos_clientes,
                         estados_proyecto=estados_proyecto,
                         cantidades_proyecto=cantidades_proyecto,
                         pagadas_recientes=pagadas_recientes,
                         pendientes_recientes=pendientes_recientes,
                         monto_pagado_reciente=monto_pagado_reciente,
                         monto_pendiente_reciente=monto_pendiente_reciente,
                         
                         # Proyectos recientes
                         proyectos_recientes=proyectos_recientes)

# RUTAS DE CLIENTES
# -----------------

@app.route('/clientes')
@login_required
def listar_clientes():
    clientes = Cliente.query.all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    if request.method == 'POST':
        cliente = Cliente(
            nombre_empresa=request.form.get('nombre_empresa'),
            contacto=request.form.get('contacto'),
            email=request.form.get('email'),
            telefono=request.form.get('telefono'),
            direccion=request.form.get('direccion')
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('listar_clientes'))
    
    return render_template('cliente_form.html')

@app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        cliente.nombre_empresa = request.form.get('nombre_empresa')
        cliente.contacto = request.form.get('contacto')
        cliente.email = request.form.get('email')
        cliente.telefono = request.form.get('telefono')
        cliente.direccion = request.form.get('direccion')
        
        db.session.commit()
        flash('Cliente actualizado', 'success')
        return redirect(url_for('listar_clientes'))
    
    return render_template('cliente_form.html', cliente=cliente)

@app.route('/clientes/<int:id>/eliminar')
@login_required
def eliminar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente eliminado', 'success')
    return redirect(url_for('listar_clientes'))

# RUTAS DE PROYECTOS
# ------------------

@app.route('/proyectos')
@login_required
def listar_proyectos():
    proyectos = Proyecto.query.all()
    return render_template('proyectos.html', proyectos=proyectos)

@app.route('/proyectos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_proyecto():
    if request.method == 'POST':
        proyecto = Proyecto(
            nombre=request.form.get('nombre'),
            descripcion=request.form.get('descripcion'),
            cliente_id=request.form.get('cliente_id'),
            responsable_id=request.form.get('responsable_id'),
            presupuesto=float(request.form.get('presupuesto', 0)),
            estado=request.form.get('estado', 'activo')
        )
        
        fecha_entrega = request.form.get('fecha_entrega')
        if fecha_entrega:
            proyecto.fecha_entrega = datetime.strptime(fecha_entrega, '%Y-%m-%d')
        
        db.session.add(proyecto)
        db.session.commit()
        flash('Proyecto creado', 'success')
        return redirect(url_for('listar_proyectos'))
    
    clientes = Cliente.query.all()
    consultores = Usuario.query.all()
    return render_template('proyecto_form.html', clientes=clientes, consultores=consultores)

# RUTAS DE EMPLEADOS (USUARIOS)
# ------------------------------

@app.route('/empleados')
@login_required
def listar_empleados():
    if current_user.rol != 'admin':
        flash('No tienes permisos para ver esta página', 'error')
        return redirect(url_for('dashboard'))
    
    empleados = Usuario.query.all()
    return render_template('empleados.html', empleados=empleados)

@app.route('/empleados/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_empleado():
    if current_user.rol != 'admin':
        flash('No tienes permisos', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        empleado = Usuario(
            nombre=request.form.get('nombre'),
            email=request.form.get('email'),
            rol=request.form.get('rol', 'consultor')
        )
        empleado.set_password(request.form.get('password', '123456'))
        
        db.session.add(empleado)
        db.session.commit()
        flash('Empleado creado', 'success')
        return redirect(url_for('listar_empleados'))
    
    return render_template('empleado_form.html')

# RUTAS DE FACTURAS
# -----------------

@app.route('/facturas')
@login_required
def listar_facturas():
    facturas = Factura.query.all()
    return render_template('facturas.html', facturas=facturas)

@app.route('/facturas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_factura():
    if request.method == 'POST':
        # Generar número de factura
        ultima_factura = Factura.query.order_by(Factura.id.desc()).first()
        if ultima_factura and ultima_factura.numero_factura:
            try:
                ultimo_numero = int(ultima_factura.numero_factura.split('-')[-1])
                nuevo_numero = f"FAC-{datetime.now().year}-{ultimo_numero + 1:04d}"
            except:
                nuevo_numero = f"FAC-{datetime.now().year}-0001"
        else:
            nuevo_numero = f"FAC-{datetime.now().year}-0001"
        
        # 1. RECUPERAR LOS DETALLES DEL FORMULARIO
        conceptos = request.form.getlist('concepto[]')
        cantidades = request.form.getlist('cantidad[]')
        precios = request.form.getlist('precio_unitario[]')
        
        # 2. CALCULAR TOTAL Y CREAR DETALLES
        total_factura = 0
        detalles = []
        
        for i in range(len(conceptos)):
            if conceptos[i] and conceptos[i].strip():
                cantidad = int(cantidades[i]) if i < len(cantidades) else 1
                precio = float(precios[i]) if i < len(precios) else 0
                subtotal = cantidad * precio
                total_factura += subtotal
                
                detalle = DetalleFactura(
                    concepto=conceptos[i],
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal
                )
                detalles.append(detalle)
        
        # 3. CREAR FACTURA (con el total calculado)
        factura = Factura(
            numero_factura=nuevo_numero,
            proyecto_id=request.form.get('proyecto_id'),
            creador_id=current_user.id,
            monto=total_factura,  # <-- AHORA: monto viene de la suma de detalles
            fecha_emision=datetime.strptime(request.form.get('fecha_emision'), '%Y-%m-%d') if request.form.get('fecha_emision') else datetime.now(),
            fecha_vencimiento=datetime.strptime(request.form.get('fecha_vencimiento'), '%Y-%m-%d') if request.form.get('fecha_vencimiento') else None,
            pagada='pagada' in request.form,
            metodo_pago=request.form.get('metodo_pago')
        )
        
        # 4. GUARDAR FACTURA Y DESPUÉS SUS DETALLES
        db.session.add(factura)
        db.session.flush()  # Para obtener el ID de la factura antes de commit
        
        for detalle in detalles:
            detalle.factura_id = factura.id
            db.session.add(detalle)
        
        db.session.commit()
        flash('Factura creada con éxito', 'success')
        return redirect(url_for('listar_facturas'))
    
    proyectos = Proyecto.query.all()
    return render_template('factura_form.html', proyectos=proyectos)

@app.route('/facturas/<int:id>/pagar')
@login_required
def pagar_factura(id):
    factura = Factura.query.get_or_404(id)
    factura.pagada = True
    db.session.commit()
    flash('Factura marcada como pagada', 'success')
    return redirect(url_for('listar_facturas'))

@app.route('/facturas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_factura(id):
    factura = Factura.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol != 'admin' and factura.creador_id != current_user.id:
        flash('No tienes permisos para editar esta factura', 'error')
        return redirect(url_for('listar_facturas'))
    
    # No permitir editar facturas pagadas
    if factura.pagada:
        flash('No se puede editar una factura ya pagada', 'error')
        return redirect(url_for('listar_facturas'))
    
    if request.method == 'POST':
        try:
            # Iniciar transacción
            db.session.begin_nested()
            
            # Actualizar cabecera
            factura.fecha_emision = datetime.strptime(request.form.get('fecha_emision'), '%Y-%m-%d') if request.form.get('fecha_emision') else factura.fecha_emision
            factura.fecha_vencimiento = datetime.strptime(request.form.get('fecha_vencimiento'), '%Y-%m-%d') if request.form.get('fecha_vencimiento') else None
            factura.metodo_pago = request.form.get('metodo_pago')
            factura.pagada = 'pagada' in request.form
            
            # Procesar detalles
            conceptos = request.form.getlist('concepto[]')
            cantidades = request.form.getlist('cantidad[]')
            precios = request.form.getlist('precio_unitario[]')
            
            if len(conceptos) == 0 or not conceptos[0].strip():
                raise ValueError('La factura debe tener al menos un concepto')
            
            # Eliminar detalles antiguos
            DetalleFactura.query.filter_by(factura_id=factura.id).delete()
            
            # Crear nuevos detalles
            total_factura = 0
            for i in range(len(conceptos)):
                if conceptos[i] and conceptos[i].strip():
                    cantidad = int(cantidades[i]) if i < len(cantidades) else 1
                    precio = float(precios[i]) if i < len(precios) else 0
                    subtotal = cantidad * precio
                    total_factura += subtotal
                    
                    detalle = DetalleFactura(
                        factura_id=factura.id,
                        concepto=conceptos[i],
                        cantidad=cantidad,
                        precio_unitario=precio,
                        subtotal=subtotal
                    )
                    db.session.add(detalle)
            
            factura.monto = total_factura
            db.session.commit()
            flash('Factura actualizada con éxito', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'error')
            return redirect(url_for('editar_factura', id=id))
        
        return redirect(url_for('listar_facturas'))
    
    proyectos = Proyecto.query.all()
    return render_template('factura_form.html', factura=factura, proyectos=proyectos)

# Iniciar la aplicación
# ============================================
# FINAL: ARRANQUE DE LA APLICACIÓN
# ============================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea tablas si no existen
    app.run(debug=True)

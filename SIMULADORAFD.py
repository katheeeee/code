import tkinter as tk

transiciones = {
    ('q0', '0'): 'q1',
    ('q0', '1'): 'q0',

    ('q1', '0'): 'q1',
    ('q1', '1'): 'q2',

    ('q2', '0'): 'q1',
    ('q2', '1'): 'q0',
}

estado_actual = "q0"
cadena = ""
indice = 0

root = tk.Tk()
root.title("Simulación AFD")
root.geometry("900x600")

canvas = tk.Canvas(root, width=900, height=400, bg="white")
canvas.pack()


pos = {
    "q0": (150,200),
    "q1": (420,200),
    "q2": (690,200)
}

circulos = {}

def dibujar_automata():

    canvas.delete("all")

    # Flecha inicio
    canvas.create_line(40,200,110,200,arrow=tk.LAST,width=2)
    canvas.create_text(70,180,text="Inicio",font=("Arial",12))

    # Transiciones

    # q0 -> q1
    canvas.create_line(190,200,380,200,arrow=tk.LAST,width=2)
    canvas.create_text(285,180,text="0",font=("Arial",12))

    # q1 -> q2
    canvas.create_line(460,200,650,200,arrow=tk.LAST,width=2)
    canvas.create_text(555,180,text="1",font=("Arial",12))

    # q2 -> q1
    canvas.create_line(650,220,460,220,arrow=tk.LAST,width=2)
    canvas.create_text(555,245,text="0",font=("Arial",12))

    # q1 -> q0
    canvas.create_line(380,180,190,180,arrow=tk.LAST,width=2)
    canvas.create_text(285,155,text="1",font=("Arial",12))

    # Bucle q0
    canvas.create_arc(120,120,180,180,start=0,extent=300,
                      style="arc",width=2)
    canvas.create_text(150,95,text="1")

    # Bucle q1
    canvas.create_arc(390,120,450,180,start=0,extent=300,
                      style="arc",width=2)
    canvas.create_text(420,95,text="0")

    # q2 -> q0
    canvas.create_line(690,240,150,260,smooth=True,arrow=tk.LAST,width=2)
    canvas.create_text(420,300,text="1")

    # Estados

    for estado in pos:

        x,y = pos[estado]

        color="white"

        if estado==estado_actual:
            color="lightgreen"

        canvas.create_oval(x-40,y-40,x+40,y+40,
                           fill=color,width=3)

        if estado=="q2":
            canvas.create_oval(x-34,y-34,x+34,y+34,width=2)

        canvas.create_text(x,y,text=estado,font=("Arial",18,"bold"))

dibujar_automata()


lblCadena = tk.Label(root,text="",font=("Arial",16))
lblCadena.pack()

lblEstado = tk.Label(root,text="",font=("Arial",16))
lblEstado.pack()

lblResultado = tk.Label(root,text="",font=("Arial",18,"bold"))
lblResultado.pack()


frame=tk.Frame(root)
frame.pack()

entrada=tk.Entry(frame,font=("Arial",16),width=20)
entrada.pack(side=tk.LEFT)


def iniciar():

    global estado_actual,cadena,indice

    cadena=entrada.get()

    if cadena=="":
        return

    estado_actual="q0"
    indice=0

    lblResultado.config(text="",fg="black")

    dibujar_automata()

    avanzar()

def avanzar():

    global estado_actual,indice

    lblCadena.config(
        text=f"Cadena: {cadena}"
    )

    lblEstado.config(
        text=f"Estado actual: {estado_actual}"
    )

    dibujar_automata()

    if indice>=len(cadena):

        if estado_actual=="q2":
            lblResultado.config(
                text="CADENA ACEPTADA",
                fg="green"
            )
        else:
            lblResultado.config(
                text="CADENA RECHAZADA",
                fg="red"
            )

        return

    simbolo=cadena[indice]

    estado_actual=transiciones[(estado_actual,simbolo)]

    indice+=1

    root.after(1000,avanzar)


btn=tk.Button(root,text="Simular",
              font=("Arial",14),
              command=iniciar)

btn.pack(pady=20)

root.mainloop()

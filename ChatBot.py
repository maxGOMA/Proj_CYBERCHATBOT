import re
import json


with open("BBDD.json", "r") as f:
    data = json.load(f)



def remove_extras(text):
    text = text.lower()
    text = re.sub(r"[^a-záéíóúüñ0-9\s]", " ", text) # basicamente reemplaza signos raros (todo aquello que no sea ni letra ni numero) por un espacio
    tokens = text.split()
    return tokens



def detectProblem(text):
    tokens = remove_extras(text)
    clean_text = " ". join(tokens)

    best_problem = None
    best_score = 0

    for problem, info in data.items():
        score = 0

        for keyword in info["keywords"]:
            if " " in keyword:
                if keyword in clean_text:
                    score += 2
            else:
                if keyword in tokens:
                    score += 1
                
        if score > best_score:
            best_score = score
            best_problem = problem

    if best_score > 0:
        return best_problem
    else:
        return None



def yesNo(text):
    tokens = remove_extras(text)

    yesWords = ["si", "sí", "claro", "exacto", "correcto", "vale"]
    noWords = ["no", "nunca", "jamas", "jamás"]

    for word in tokens:
        if word in yesWords:
            return "yes"
        if word in noWords:
            return "no"
    return "unknown"



def finalAnswer(problem, text):
    
    answerType = yesNo(text)
    info = data[problem]

    if answerType == "yes":
        return info["possible_yes"] + "\n" + info["advice_yes"]
    
    elif answerType == "no":
        return info["possible_no"] + "\n" + info["advice_no"]
    
    else:
        return "No he entendido tu respuesta, como recomendación por regla general: " + info["advice_yes"]



def isThanks(text):
    thanksWords = ["gracias", "muchas gracias", "agradecida", "agradecido", "aprecio", "apreciado", "apreciada", ""]
    tokens = remove_extras(text)

    for word in tokens:
        if word in thanksWords:
            return True
    return False



def isGoodbye(text):
    goodbye_words = ["adios", "adiós", "hasta", "chao", "bye", "salir"]
    tokens = remove_extras(text)

    for word in tokens:
        if word in goodbye_words:
            return True
    return False



def isGreeting(text):
    greeting_words = ["hola", "buenas", "hey", "buenos", "saludos"]
    tokens = remove_extras(text)

    for word in tokens:
        if word in greeting_words:
            return True
    return False



# Función del bucle principal 
def chatBot():
    print("Chatbot: Hola. Soy un chatbot de ayuda en ciberseguridad.")
    print("Chatbot: Cuénteme que error visualiza en su dispositivo.")
    print("Chatbot: Escriba 'salir' si quiere acabar la sesion.\n")

    current_problem = None # variable que indica el valor donde se halla el problema que creemos que el usuario tiene

    while True:
        user_text = input("Tu: ")

        if current_problem is None:
            current_problem = detectProblem(user_text)

            if current_problem is None:
                print("Chatbot: No estoy seguro de lo que ocurre.")
                print("Chatbot: Prueba a explicarlo con frases como:")
                print("Chatbot: 'me salen anuncios raros', 'recibí un mensaje sospechoso', 'mi cuenta fue hackeada' o 'el móvil va muy lento'.")
            else:
                print("Chatbot ", data[current_problem]['question'])

        else: 
            answer = finalAnswer(current_problem, user_text)
            print("Chatbot: ", answer)
            current_problem = None
            
            print("Chatbot: Si quieres, puedes contarme otro problema diferente.")
            user_text = input("Tu: ")

            if isThanks(user_text):
                print("Chatbot: De nada. Si quieres puedes contarme otro problema.")

            elif isGreeting(user_text):
                print("Chatbot: Hola. Explicame qué problema notas en tu dispositivo.")

            if isGoodbye(user_text):
                print("Chatbot: Espero haberte ayudado. Hasta luego!")
                break             


# ejecuta todo el programa
chatBot()

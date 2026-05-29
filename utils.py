import random
import string
import os
import shutil
import email
import imaplib
import time
import json
import cv2
import numpy
import base64
import socket
from screeninfo import get_monitors

def write_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    f.close()

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    f.close()
    return data
        
def encode_image(path):
    image = cv2.imread(path)
    _, image_encoded = cv2.imencode('.jpg', image)
    base64_encoded = base64.b64encode(image_encoded).decode('utf-8')
    return base64_encoded

def decode_image(base64_encoded_data):
    base64_decoded_data = base64.b64decode(base64_encoded_data)
    image_array = numpy.frombuffer(base64_decoded_data, dtype=numpy.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def choice_reaction():
    list_reaction = ['Thích', 'Yêu thích', 'Thương thương']
    return random.choice(list_reaction)


def sleep_very_short():
    return time.sleep(random.choice([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]))


def sleep_short():
    return time.sleep(random.choice(range(2, 5)))


def sleep_long():
    return time.sleep(random.choice(range(5, 10)))


def sleep_very_long():
    return time.sleep(random.choice(range(8, 20)))


def sleep_very_very_long():
    return time.sleep(random.choice(range(20, 60)))

def read_file_to_list(path):
    try:
        with open(path, "r") as f:
            content_list = f.readlines()
            return content_list
    except UnicodeDecodeError:
        print("Error: Unable to decode file. Try specifying encoding.")

def read_file(path):
    try:
        with open(path,"r") as f:
            content = f.read()
            return content
    except UnicodeDecodeError:
        print("Error: Unable to decode file. Try specifying encoding.")

def write_file(path, content):
    with open(path, 'w', encoding="utf8") as f:
        for line in content:
            f.write(f"{line}\n")

def write_file_a(path, content):
    with open(path, 'a', encoding="utf8") as f:
        for line in content:
            f.write(f"{line}\n")

def write_string_to_file(path, content):
    with open(path, 'a', encoding="utf8") as f:
        f.write(f"{content}\n")

def write_list_to_file(path, content_list):
    with open(path, 'w') as file:
        for item in content_list:
            file.write(f"{item}\n")
    file.close()

def remove_file_or_folder(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
            return f"File '{path}' has been removed."
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return f"Folder '{path}' and its contents have been removed."
        else:
            return f"No file or folder found at '{path}'."
    except Exception as e:
        return f"Error: {e}"
    
def move_file_or_folder(path_old, path_new):
    try:
        shutil.move(path_old, path_new)
        print(f"Moved '{path_old}' to '{path_new}'.")
        return True
    except Exception as e:
        print(f"Failed to move '{path_old}' to '{path_new}'. Reason: {e}")
        return False
    
def copy_file_or_folder(path_old, path_new):
    print(path_old)
    try:
        if os.path.isfile(path_old):
            shutil.copy(path_old, path_new)
            print(f"File copied successfully from {path_old} to {path_new}.")
        elif os.path.isdir(path_old):
            if os.path.exists(path_new):
                shutil.copytree(path_old, path_new, dirs_exist_ok=True)
            else:
                shutil.copytree(path_old, path_new)
            print(f"Folder copied successfully from {path_old} to {path_new}.")
        else:
            print("The source path does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_folder(folder_path):
    try:
        os.makedirs(folder_path)
        print(f"Folder created at {folder_path}")
        return True
    except OSError as e:
        print(f"Failed to create folder at {folder_path}: {e}")
        return False
    
def file_search(path):
    if not os.path.exists(path):
        return "Thư mục không tồn tại."
    files_and_directories = os.listdir(path)
    return files_and_directories

def random_number(number):
    random_so = ''.join(random.choices(string.digits, k=number))
    return random_so

def random_password():
    k = random_name("viet")+random_chars(3)+"@"+random_number(3)
    return k

def random_chars(number_chars):
    random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=number_chars))
    return random_chars

def random_name(type_name):
    if type_name == "viet":
        k = random.choice(['An','Anh','Ban','Binh','Bich','Bang','Bach','Bao','Bang','Boi','Ca','Cam','Chi','Chinh','Chieu','Chung','Chau','Cat','Cuc','Cuong','Cam','Cam','Dao','Di','Dien','Diem','Diep','Dieu','Du','Dung','Duy','Duyen','Dan','Da','Duong','Da','Gia','Giang','Giao','Giang','Hieu','Hien','Hieu','Hiep','Hoa','Hoan','Hoai','Hoan','Hoang','Hoa','Huyen','Hue','Huynh','Ha','Ham','Han','Hoa','Huong','Huong','Huong','Huong','Ha','Hac','Hanh','Hai','Hao','Hau','Hang','Hoa','Ho','Hong','Hop','Khai','Khanh','Khiet','Khuyen','Khue','Khanh','Khe','Khoi','Khuc','Kha','Khai','Kim','Kiet','Kieu','Ke','Ky','Lam','Lan','Linh','Lien','Lieu','Loan','Ly','Lam','Le','Ly','Lang','Luu','Le','Le','Loc','Loi','Luc','Mai','Mi','Minh','Mien','My','Man','Mau','Moc','Mong','My','Nga','Nghi','Nguyen','Nguyet','Nguyet','Nga','Ngan','Ngon','Ngoc','Nhan','Nhi','Nhien','Nhung','Nhan','Nhan','Nha','Nhon','Nhu','Nhan','Nhat','Nhat','Nuong','Nu','Oanh','Phi','Phong','Phuc','Phuong','Phuoc','Phuong','Phung','Quyen','Quan','Que','Quynh','Sa','San','Sao','Sinh','Song','Song','Son','Suong','Thanh','Thi','Thien','Thieu','Thieu','Thien','Thoa','Thoai','Thu','Thuan','Thuan','Thy','Thai','Theu','Thong','Thuy','Thuy','Tho','Thu','Thuong','Thuong','Thach','Thao','Tham','Thuc','Thuy','Thuy','Tinh','Tien','Tieu','Trang','Tranh','Trinh','Trieu','Trieu','Trung','Tra','Tram','Tran','Truc','Tram','Tuyen','Tuyet','Tuyen','Tue','Ty','Tam','Tung','Tuy','Tu','Tuy','Tuong','Tinh','To','Tu','Uyen','Uyen','Vi','Vinh','Viet','Vy','Vang','Vanh','Van','Vu','Vong','Vy','Xuyen','Xuan','Yen','Yen','xanh','Ai','Anh','An','Y','Dan','Dinh','Doan','Dai','Dao','Dong','Dang','Don','Duc'])
        return k
    else:
        k = random.choice(['James','John','Robert','Michael','William','David','Richard','Charles','Joseph','Thomas','Christopher','Daniel','Paul','Mark','Donald','George','Kenneth','Steven','Edward','Brian','Ronald','Anthony','Kevin','Jason','Matthew','Gary','Timothy','Jose','Larry','Jeffrey','Frank','Scott','Eric','Stephen','Andrew','Raymond','Gregory','Joshua','Jerry','Dennis','Walter','Patrick','Peter','Harold','Douglas','Henry','Carl','Arthur','Ryan','Roger','Joe','Juan','Jack','Albert','Jonathan','Justin','Terry','Gerald','Keith','Samuel','Willie','Ralph','Lawrence','Nicholas','Roy','Benjamin','Bruce','Brandon','Adam','Harry','Fred','Wayne','Billy','Steve','Louis','Jeremy','Aaron','Randy','Howard','Eugene','Carlos','Russell','Bobby','Victor','Martin','Ernest','Phillip','Todd','Jesse','Craig','Alan','Shawn','Clarence','Sean','Philip','Chris','Johnny','Earl','Jimmy','Antonio','Danny','Bryan','Tony','Luis','Mike','Stanley','Leonard','Nathan','Dale','Manuel','Rodney','Curtis','Norman','Allen','Marvin','Vincent','Glenn','Jeffery','Travis','Jeff','Chad','Jacob','Lee','Melvin','Alfred','Kyle','Francis','Bradley','Jesus','Herbert','Frederick','Ray','Joel','Edwin','Don','Eddie','Ricky','Troy','Randall','Barry','Alexander','Bernard','Mario','Leroy','Francisco','Marcus','Micheal','Theodore','Clifford','Miguel','Oscar','Jay','Jim','Tom','Calvin','Alex','Jon','Ronnie','Bill','Lloyd','Tommy','Leon','Derek','Warren','Darrell','Jerome','Floyd','Leo','Alvin','Tim','Wesley','Gordon','Dean','Greg','Jorge','Dustin','Pedro','Derrick','Dan','Lewis','Zachary','Corey','Herman','Maurice','Vernon','Roberto','Clyde','Glen','Hector','Shane','Ricardo','Sam','Rick','Lester','Brent','Ramon','Charlie','Tyler','Gilbert','Gene','Marc','Reginald','Ruben','Brett','Angel','Nathaniel','Rafael','Leslie','Edgar','Milton','Raul','Ben','Chester','Cecil','Duane','Franklin','Andre','Elmer','Brad','Gabriel','Ron','Mitchell','Roland','Arnold','Harvey','Jared','Adrian','Karl','Cory','Claude','Erik','Darryl','Jamie','Neil','Jessie','Christian','Javier','Fernando','Clinton','Ted','Mathew','Tyrone','Darren','Lonnie','Lance','Cody','Julio','Kelly','Kurt','Allan','Nelson','Guy','Clayton','Hugh','Max','Dwayne','Dwight','Armando','Felix','Jimmie','Everett','Jordan','Ian','Wallace','Ken','Bob','Jaime','Casey','Alfredo','Alberto','Dave','Ivan','Johnnie','Sidney','Byron','Julian','Isaac','Morris','Clifton','Willard','Daryl','Ross','Virgil','Andy','Marshall','Salvador','Perry','Kirk','Sergio','Marion','Tracy','Seth','Kent','Terrance','Rene','Eduardo','Terrence','Enrique','Freddie','Wade'])
        return k
       
def get_code_email(EMAIL, PASSWORD):
    SERVER = 'outlook.office365.com'
    
    try:
        number_fail = 0
        while number_fail < 3: 
            try:
                try:
                    mail = imaplib.IMAP4_SSL(SERVER)
                    mail.login(EMAIL, PASSWORD)

                    x = mail.select('Inbox')  #readonly=True
                    num = x[1][0].decode('utf-8')
                    # from here you can start a loop of how many mails you want, if 10, then num-9 to num
                    resp, lst = mail.fetch(num, '(RFC822)')
                    body = lst[0][1]
                    email_message = email.message_from_bytes(body)
                    
                    code = email_message['Subject'][:6]
                    print("code: ", code)
                    if code.isdigit():
                        return code 
                    else:
                        # Đọc inbox
                        x = mail.select('Junk')  #readonly=True
                        num = x[1][0].decode('utf-8')
                        # from here you can start a loop of how many mails you want, if 10, then num-9 to num
                        resp, lst = mail.fetch(num, '(RFC822)')
                        body = lst[0][1]
                        email_message = email.message_from_bytes(body)
                        
                        code = email_message['Subject'][:6]
                        if code.isdigit():
                            print("number_fail:  ",EMAIL,  number_fail)
                            return code 
                        else:
                            number_fail += 1
                            time.sleep(2)
                            print("number_fail:  ",EMAIL,  number_fail)
                except:
                    # Đọc inbox
                    x = mail.select('Junk')  #readonly=True
                    num = x[1][0].decode('utf-8')
                    # from here you can start a loop of how many mails you want, if 10, then num-9 to num
                    resp, lst = mail.fetch(num, '(RFC822)')
                    body = lst[0][1]
                    email_message = email.message_from_bytes(body)
                    
                    code = email_message['Subject'][:6]
                    if code.isdigit():
                        print("number_fail:  ",EMAIL,  number_fail)
                        return code 
                    else:
                        number_fail += 1
                        time.sleep(2)
                        print("number_fail:  ",EMAIL,  number_fail)
                    
            except Exception as error:
                number_fail += 1
                time.sleep(2)

        # Đọc inbox
        x = mail.select('Junk')  #readonly=True
        num = x[1][0].decode('utf-8')
        # from here you can start a loop of how many mails you want, if 10, then num-9 to num
        resp, lst = mail.fetch(num, '(RFC822)')
        body = lst[0][1]
        email_message = email.message_from_bytes(body)
        
        code = email_message['Subject'][:6]
        return code 
        
    except Exception as error:
        return "Không đăng nhập được vào mail"



def convert_json_to_string(json_obj):
    json_string = json.dumps(json_obj)
    return json_string

def convert_to_json(string):
    try:
        json_object = json.loads(string)
        return json_object
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None
def random_user_angent():
    userAgents = [
                    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/528.11 (KHTML, like Gecko) Chrome/2.0.157.0 Safari/528.11",
                    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/528.9 (KHTML, like Gecko) Chrome/2.0.157.0 Safari/528.9",
                    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/528.11 (KHTML, like Gecko) Chrome/2.0.157.0 Safari/528.11",
                    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/528.10 (KHTML, like Gecko) Chrome/2.0.157.0 Safari/528.10",
                    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/528.10 (KHTML, like Gecko) Chrome/2.0.157.2 Safari/528.10",
                    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/528.10 (KHTML, like Gecko) Chrome/2.0.157.2 Safari/528.10",
                    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_0; en-US) AppleWebKit/528.10 (KHTML, like Gecko) Chrome/2.0.157.2 Safari/528.10",
                    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.53 Safari/525.19",
                    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.53 Safari/525.19",
                    "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.53 Safari/525.19",
                    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.53 Safari/525.19",
                    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.999 Safari/533.4",
                    "Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.99 Safari/533.4",
                    "Mozilla/5.0 (X11; U; Linux i686; es-ES; rv:1.8.0.7) Gecko/20060830 Firefox/1.5.0.7 (Debian-1.5.dfsg+1.5.0.7-1~bpo.1)"
                    ]
    random_user_agent = random.choice(userAgents)
    return random_user_agent


def getRandomPort(port):
    random_tmp = 0
    while True:
        if port == None:
            port = random.randint(1000, 35000)
        else:
            port = port + random_tmp
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            random_tmp = random.choice(range(111,999))
            continue
        else:
            return port

def get_pos(index, w, h):
    for m in get_monitors():
        if m.is_primary == True:
            num_browser_x = m.width // w
    x = index % num_browser_x * w
    if index < num_browser_x:
        y = 0
    else:
        y = index//num_browser_x * h
    return x, y




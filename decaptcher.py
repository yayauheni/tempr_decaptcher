from skimage import data, io, filters
from IPython.display import Image
from PIL import ImageDraw

import pytesseract
import requests
import os.path
import hashlib
import PIL
import cv2
import sys
import re

sys.setrecursionlimit(4000)  

# decaptcher for tempr.email
class Decaptcher:
    CAPTCHA_FOLDER = 'tempr_captcha'
    
    def __init__(self, sid, headers = {}, cookies = {}):
        self.sid = sid
        self.headers = headers
        self.cookies = cookies
    
    def download_image(self):
        captcha_url = f'https://tempr.email/application/api/secureCaptcha.php?sid={self.sid}&small=1'
        img_data = requests.get(captcha_url, headers = self.headers, cookies = self.cookies).content
        img_md5 = hashlib.md5(img_data).hexdigest()
        img_path = os.path.join(self.CAPTCHA_FOLDER, img_md5 + '.png')
        with open(img_path, 'wb') as handler:
            handler.write(img_data)
        return img_path
    
    def image_to_bw(self, image_path):
        img = PIL.Image.open(image_path)
        pixels = img.load()
        for i in range(100):
            for j in range(50):
                if j < 24 and i < 99:
                    pixels[i, j] = (0, 0, 0) if pixels[i, j][2] > 115 else (255, 255, 255)
                else:
                    pixels[i, j] = (0, 0, 0) if pixels[i, j][2] < 255 else (255, 255, 255)
        bw_img_path = re.sub(r"\.png$", "_bw.png", image_path)
        img.save(bw_img_path)
        return bw_img_path
    
    def recursive_traversal(self, x, y, pixels, area, rect=None):
        area.append([x, y])
        if rect is not None:
            rect['x1'] = min(rect['x1'], x)
            rect['y1'] = min(rect['y1'], y)
            rect['x2'] = max(rect['x2'], x)
            rect['y2'] = max(rect['y2'], y)
        if x - 1 >= 0 and pixels[x - 1, y] == (255, 255, 255) and [x - 1, y] not in area:
            self.recursive_traversal(x - 1, y, pixels, area, rect)
        if x + 1 < 100 and pixels[x + 1, y] == (255, 255, 255) and [x + 1, y] not in area:
            self.recursive_traversal(x + 1, y, pixels, area, rect)
        if y - 1 >= 0 and pixels[x, y - 1] == (255, 255, 255) and [x, y - 1] not in area:
            self.recursive_traversal(x, y - 1, pixels, area, rect)
        if y + 1 < 50 and pixels[x, y + 1] == (255, 255, 255) and [x, y + 1] not in area:
            self.recursive_traversal(x, y + 1, pixels, area, rect)
    
    def fill_area(self, pixels, area, color):
        for cords in area:
            pixels[cords[0], cords[1]] = color

    def fill_background(self, pixels):
        area = []
        self.recursive_traversal(0, 0, pixels, area)
        self.fill_area(pixels, area, (0, 0, 0))
    
    def outline_characters(self, draw, img, image_path, characters):
        for character in characters[:3]:
            draw.rectangle([(character['x1'], character['y1']), (character['x2'], character['y2'])], outline ="red")   
        outlined_image_path = re.sub(r"\.png$", "_outlined.png", image_path)
        img.save(outlined_image_path)
    
    def highlight_characters(self, image_path):
        img = PIL.Image.open(image_path)
        draw = ImageDraw.Draw(img)
        pixels = img.load()
        self.fill_background(pixels)
        characters = []
        for i in range(100):
            for j in range(50):
                if pixels[i, j] == (255, 255, 255):
                    area = []
                    rect = {"x1": i, "y1": j, "x2": i, "y2": j}
                    self.recursive_traversal(i, j, pixels, area, rect)
                    self.fill_area(pixels, area, (0, 255, 0))
                    rect['square'] = (rect['x2'] - rect['x1']) * (rect['y2'] - rect['y1'])
                    rect['area'] = area
                    characters.append(rect)
        
        characters.sort(key=lambda x: x['square'], reverse=True)
        self.outline_characters(draw, img, image_path, characters[:3])
        draw.rectangle([(0, 0), (100, 50)], fill='white', outline ='white')
        for character in characters[:3]:
            self.fill_area(pixels, character['area'], (0, 0, 0))  
        filled_image_path = re.sub(r"\.png$", "_filled.png", image_path)
        img.save(filled_image_path)
        return filled_image_path   

    def img_to_text(self, image_path):
        text = pytesseract.image_to_string(PIL.Image.open(image_path), config='-c tessedit_char_whitelist=123456789ABCDEFGHKLNPRSTUVXYZ')
        return text
    
    def solve_captcha(self, captcha_url):
        captcha_image = self.download_image()
        bw_captcha_image = self.image_to_bw(captcha_image)
        highlighted_characters_image = self.highlight_characters(bw_captcha_image)
        text = self.img_to_text(highlighted_characters_image)
        return text

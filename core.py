from edit import *
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import re
from datetime import datetime


class Collage():
    """ Class describing an image collage """

    def __init__(self, root, title, subtitle, Time, notes, path, pic_list):
        self.root = root
        self.title = title
        self.subtitle = subtitle
        self.time = Time
        self.notes = notes
        self.path = path
        self.pic_list = pic_list
        self.collage_pic_window = None
        self.export_dir = ""
        self.picture_name = ""

        # if pic_list empty, raise error
        if not self.pic_list:
            raise ValueError("List of pictures is empty")

    def __repr__(self):
        """" override print method """

        values = (self.title, self.subtitle, self.time, self.batch, self.description, self.path)
        to_print = "\n".join(v for v in values if v)
        return to_print

    def generate_template(self, template_id):
        """ generates a template for the collage """

        pic_nb = len(self.pic_list)
        template_pic_nb = int(template_id.split('_')[1])

        # if template does not match the number of pictures, find a matching one
        if pic_nb != template_pic_nb:
            template_id = f"T_{str(pic_nb).zfill(2)}_01"
            self.print_to_log("Selected template does not match number of pictures > Looking for a matching template.")

        # get path to json file
        template_id_path = os.path.join(SETTINGS['TEMPLATE_DIR'], template_id + ".json")

        # if json file does not exist, raise error
        if not os.path.isfile(template_id_path):
            raise OSError("Could not find a matching template json file, create one")

        # load template file contents
        with open(f"{os.path.join(SETTINGS['TEMPLATE_DIR'], template_id)}.json") as f:
            template_layout = json.load(f)

        # store picture paths as keys and get values from json file
        pic_dic = {}

        for idx, pic in enumerate(self.pic_list):
            pic_path = os.path.join(self.path, pic)
            pic_dic[pic_path] = tuple(template_layout[str(idx + 1)])

        # get description values from json file
        pic_dic['Description'] = tuple(template_layout['Description'])

        # store logo path as key and get values from json file
        pic_dic[SETTINGS['COCO_LOGO']] = tuple(template_layout['Logo'])

        return pic_dic

    def collage_auto(self, pic_dic, show_pic):
        """ automatically create and export picture based on a dict of paths and resolution (no ui, no edit) """

        # create empty picture
        collage_pic = Image.new(mode="RGBA", size=(SETTINGS['COLLAGE_WIDTH'], SETTINGS['COLLAGE_HEIGHT']),
                               color=tuple(SETTINGS['BKG_COLOR']))

        # paste pictures into it
        if isinstance(pic_dic, dict):
            for key, value in pic_dic.items():

                # data missing or not specified
                if not (key and value):
                    continue

                # get picture resolution and position
                pic_path = key
                pic_x, pic_y, pic_w, pic_h = value[0:4]

                # Add description if option enabled
                if key == 'Description':
                    if self.add_description:
                        # print key/value of the description
                        print(key, value)
                        description_text = self.format_description(value[-1])
                        # write description in picture
                        description = ImageDraw.Draw(collage_pic)
                        description.text((pic_x, pic_y), description_text,
                                        font=ImageFont.truetype(SETTINGS['TEXT_FONT'], SETTINGS['TEXT_SIZE']),
                                        fill=tuple(SETTINGS['TEXT_COLOR']))
                    continue
                
                # Add logo if option enabled
                if key == SETTINGS['COCO_LOGO'] and not self.add_logo:
                    continue
                
                # print key/value of the current picture
                print(key, value)

                # Open, reorient, resize and paste image data into review pic
                img = Image.open(pic_path).convert("RGBA")
                img = ImageOps.exif_transpose(img)
                img.thumbnail((pic_w, pic_h), Image.ANTIALIAS)
                collage_pic.paste(img, box=(pic_x, pic_y), mask=img)
        
        # screenshot title
        if self.picture_name:
            title = self.picture_name
        else:
            title = f"{self.batch}_review"

        # export dir
        if self.export_dir:
            save_path = os.path.join(self.export_dir, f'{title}.png')
        else:
            save_path = os.path.join(self.path, "export", f'{title}.png')

        Path(os.path.dirname(save_path)).mkdir(parents=True, exist_ok=True)

        # save picture, add path to clipboard and print result
        collage_pic.save(save_path)
        pyperclip.copy(save_path)
        print(f"Screenshot saved at {save_path}. Path copied to clipboard.")
        # show picture
        if show_pic:
            os.startfile(save_path)

    def format_description(self, description):
        """ Format the description """
        
        description = description.format(title=self.title, time=self.time, subtitle=self.subtitle, notes=self.notes)
        
        # get rid of unnecessary separators
        description = re.sub('( / ){2,10}', ' / ', description)
        # get rid of unnecessary line breaks
        description = re.sub('\n{2,10}', '\n', description)
        # get rid of unnecessary characters at the end
        description = re.sub('(\s*/?\s*)$', '', description)
        
        return description

    def collage_edit(self, app, review_pic_window, pic_dic):
        """ Start the PyQt collage tool to edit the collage manually using mouse shortcuts """

        # replace description infos if option enabled
        if 'Description' in pic_dic.keys():
            if self.add_description:
                description_text = self.format_description(pic_dic['Description'][-1])
                pic_dic['Description'] = *pic_dic['Description'][:4], description_text
            else:
                pic_dic.pop('Description')
    
        # remove logo from pictures if option not enabled
        if SETTINGS['COCO_LOGO'] in pic_dic.keys() and not self.add_logo:
            pic_dic.pop(SETTINGS['COCO_LOGO'])

        # create main window
        review_pic_window.populate_window(app, pic_dic, self.export_dir, self.picture_name)
        review_pic_window.show()
        review_pic_window.update_pictures()  # needs to be done AFTER showing window


    def create_collage(self, app, review_pic_window, pic_dic, show, ui=False, dir='', name='', desc=True, logo=True):
        """ creates collage with or without Edit interface """
        
        self.app = app

        # store export directory and target picture
        self.export_dir = dir
        self.picture_name = name
        self.add_description = desc
        self.add_logo = logo
        
        # load latest settings
        global SETTINGS
        SETTINGS = load_settings()

        if ui:
            self.collage_edit(app, review_pic_window, pic_dic)
        else:
            self.collage_auto(pic_dic, show)

    def print_to_log(self, string):
        ''' log message to console with time information '''
        print(f'{datetime.now().strftime("%m/%d/%Y, %H:%M:%S")} >> {string}')
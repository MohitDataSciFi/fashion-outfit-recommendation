"""
Extract the features for each ssense image, using a resnet50 with pytorch
"""

import torch
import torch.nn as nn
from torchvision import models
import torchvision.transforms as transforms

import os
import argparse
import numpy as np
from skimage.transform import resize
from skimage import img_as_ubyte
from skimage.color import gray2rgb, rgba2rgb
import skimage.io
from PIL import Image
import time
import pickle as pkl
import json
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

parser = argparse.ArgumentParser()
parser.add_argument('--phase', default='train', choices=['train', 'test', 'valid'])
args = parser.parse_args()

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# load net to extract features
model = models.resnet50(pretrained=True)
# skip last layer (the classifier)
model = nn.Sequential(*list(model.children())[:-1])
model = model.to(device)
model.eval()

normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                    std=[0.229, 0.224, 0.225])

transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize(256), transforms.CenterCrop(224),
                transforms.ToTensor(), normalize
            ])

def process_image(im):
    im = transform(im)
    im = im.unsqueeze_(0)
    im = im.to(device)
    out = model(im)
    return out.squeeze()

dataset_path = '..\\..'
images_path = r"C:\\Users\\Software\\Downloads\\polyvore-images\\images\\"
json_file = r"C:\Users\Software\Downloads\polyvore-images\jsons\test_no_dup.json"
with open(json_file) as f:
    data = json.load(f)

save_to =r"C:\Users\Software\Downloads\polyvore-images\dataset"
if not os.path.exists(save_to):
    os.makedirs(save_to)
save_dict = os.path.join(save_to, 'imgs_featdict_{}.pkl'.format(args.phase))

ids = {}

# I use img ids, but the folders use outfit_id/index.png
for outfit in data:
    for item in outfit['items']:
        # get id from the image url
        _, id = item['image'].split('id=')
        their_id = '{}_{}'.format(outfit['set_id'], item['index'])
        ids[id] = their_id

# initialize empty feature matrix that will be filled
features = {}
count = {}

print('iterating through ids')
i = 0
n_items = len(ids.keys())
with torch.no_grad(): # it is the same as volatile=True for versions before 0.4
    for id in ids:
        try:
        
            outfit_id, index = ids[id].split('_') # outfitID_index
            print(outfit_id , id)

            image_path = images_path + outfit_id + '\\' + '{}.jpg'.format(index)
            assert os.path.exists(image_path)

            im = skimage.io.imread(image_path)
            if len(im.shape) == 2:
                im = gray2rgb(im)
            if im.shape[2] == 4:
                im = rgba2rgb(im)

            im = resize(im, (256, 256))
            im = img_as_ubyte(im)

            feats = process_image(im).cpu().numpy()

            if id not in features:
                features[id] = feats
                count[id] = 0
            else:
                features[id] += feats
            count[id] += 1

            if i % 1000 == 0 and i > 0:
                print('{}/{}'.format(i, n_items))
                
            i += 1
            print(outfit_id , id)
        except:
            print("error")
            pass
feat_dict = {}
for id in features:
    feats = features[id]
    feats = np.array(feats)/count[id]
    feat_dict[id] = feats

with open(save_dict, 'wb') as handle:
    pkl.dump(feat_dict, handle, protocol=pkl.HIGHEST_PROTOCOL)

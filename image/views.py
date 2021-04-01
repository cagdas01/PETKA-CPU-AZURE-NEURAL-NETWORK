from json import JSONEncoder
from pathlib import Path
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from .Extentions.ModifiedObjectDetection import VisualizedDetectionImage
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
import cv2
import sys
import json

sys.path.append("..")

upload_folder = settings.MEDIA_ROOT


def getNonDefectBlobAccordingEnviroment(request, image):
    if request.META['HTTP_HOST'] == "127.0.0.1:8000":
        blob = BlobClient.from_connection_string(
            conn_str="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;" +
                     "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq" +
                     "2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/" +
                     "devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1",
            container_name="original-images-development",
            blob_name=image)
    else:
        blob = BlobClient.from_connection_string(
            conn_str="DefaultEndpointsProtocol=https;AccountName=petkastorage;AccountKey=mq6jxDSmfW9TPCt69h/n8ZyHHKrcVqf/+2/IjXZ/K6AtMJ9fyWq0mWmkEw+hgHOfPT7FgluHFCpO7rKhv1i30g==;EndpointSuffix=core.windows.net",
            container_name="originalimages",
            blob_name=image)
    return blob


def getDefectBlobAccordingEnviroment(request, image):
    if request.META['HTTP_HOST'] == "127.0.0.1:8000":
        blob = BlobClient.from_connection_string(
            conn_str="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;" +
                     "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq" +
                     "2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/" +
                     "devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1",
            container_name="defected-images-development",
            blob_name=image)
    else:
        blob = BlobClient.from_connection_string(
            conn_str="DefaultEndpointsProtocol=https;AccountName=petkastorage;" +
                     "AccountKey=mq6jxDSmfW9TPCt69h/n8ZyHHKrcVqf/+2/IjXZ/K6AtMJ" +
                     "9fyWq0mWmkEw+hgHOfPT7FgluHFCpO7rKhv1i30g==;EndpointSuffix" +
                     "=core.windows.net",
            container_name="defectimages",
            blob_name=image)
    return blob


def getDownloadedPathAccordingEnviroment(request, image):
    blob = getNonDefectBlobAccordingEnviroment(request, image)
    print("*****************************blobName******************************")
    print(blob)
    originalimageDir = os.path.join(upload_folder, "original-images", image)

    with open(originalimageDir, "wb") as download_file:
        download_file.write(blob.download_blob().readall())
    return os.path.join(originalimageDir)


def getUploadedPathAccordingEnviroment(request, image):
    blob = getDefectBlobAccordingEnviroment(request, image)

    originalimageDir = upload_folder + "\\defected-images\\"

    with open(originalimageDir + image, "wb"):
        blob.download_blob()
    return os.path.join(originalimageDir, image)


def index(request):
    return render(request, 'index.html', {})


def defectAnlyze(request, image):
    print("***************************cagdas karabay*********************************")
    print(request.META['HTTP_HOST'])
    originalimageFullPath = getDownloadedPathAccordingEnviroment(request, image)

    DefectionVisualizationModel = VisualizedDetectionImage(originalimageFullPath)

    classes = DefectionVisualizationModel[0].classes
    scores = DefectionVisualizationModel[0].scores
    category_index = DefectionVisualizationModel[0].category_index
    image_with_pins = DefectionVisualizationModel[0].image_with_pins

    defectModel = []

    for index, value in enumerate(classes[0]):
        if scores[0, index] > 0.20:
            if int((category_index.get(value).get('id'))) == 1:
                defectModel.append(CustomDefectModel(round(scores[0, index] * 100, 2), index + 1, 1))

            if int((category_index.get(value).get('id'))) == 2:
                defectModel.append(CustomDefectModel(round(scores[0, index] * 100, 2), index + 1, 2))

    originalImageName = Path(image).resolve().stem

    defectedImageName = originalImageName + '-defected' + '.jpg'

    defect_path = os.path.join(settings.MEDIA_ROOT, "defect-images", defectedImageName)

    cv2.imwrite(defect_path, image_with_pins)

    blob = getDefectBlobAccordingEnviroment(request, defectedImageName)

    with open(defect_path, "rb") as data:
        blob.upload_blob(data)
    # defected resmi azura upload et,
    # Yine environment tipine göre upload işlemini başlat...
    main = MainModel(defectedImageName, defectModel)  # defectedImageName olacak ..

    serializedResultData = json.dumps(main, indent=4, cls=ProductEncoder)
    return HttpResponse(serializedResultData, content_type='application/json')


class ProductEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


class CustomDefectModel:
    def __init__(self, defectRate, defectQueue, defectType):
        self.defectRate = defectRate
        self.defectQueue = defectQueue
        self.defectType = defectType


class MainModel:
    def __init__(self, defectImageName, defectDetails):
        self.name = defectImageName
        self.defectDetails = defectDetails

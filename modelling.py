###Imports
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import torch.nn as nn
from torchvision import models
from PIL import ImageFile
from preprocessing import split_train_valid_sets
from visualizing import training_visualisation

###Constants
ImageFile.LOAD_TRUNCATED_IMAGES = True
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
fpath = 'data/imagenet_class_index.json'

batch_size_preconvfeat = 128
num_epochs = 5
# Define a loss function
# in the main not a constant
# Define an optimizer function
lr = 0.01


###Main function
def main_model():
    return


###Core functions
def create_preconvfeat_loader(dataloader, model, batch_size_preconvfeat, shuffle):
    '''
    Precomputes features extraction and creates a loader to extract features.
    
    :param dataloader: dataloader
    :param model: model from which we extract feature
    :param batch_size_preconvfeat: how many samples per batch to load from the dataset containing extracted features
    :param shuffle: set to True to have the extracted features dataset reshuffled at every epoch
    :return: loaders for extracted features
    '''
    dtype = torch.float
    conv_features = []
    labels_list = []
    for data in dataloader:
        inputs, labels = data
        inputs = inputs.to(device)
        labels = labels.to(device)

        x = model.features(inputs)
        conv_features.extend(x.data.cpu().numpy())
        labels_list.extend(labels.data.cpu().numpy())

    conv_features = np.concatenate([[feat] for feat in conv_features])
    datasetfeat = [[torch.from_numpy(f).type(dtype), torch.tensor(l).type(torch.long)] for (f, l) in zip(conv_features, labels_list)]
    datasetfeat = [(inputs.reshape(-1), classes) for [inputs, classes] in datasetfeat]
    loaderfeat = torch.utils.data.DataLoader(datasetfeat, batch_size=batch_size_preconvfeat, shuffle=shuffle)

    return loaderfeat




def train_model(model, dataloader, size, epochs=1, optimizer=None, criterion=None):
    '''
    Computes loss and accuracy on validation test

    :param model: neural network model
    :param dataloader: train loader
    :param size: number of images in the dataset
    :param epochs: number of epochs
    :param optimizer: optimization algorithm
    :return:
    '''
    model.train()
    loss_list = []
    acc_list = []
    recall_list = []

    for epoch in range(epochs):
        running_loss = 0.0
        running_corrects = 0
        running_true_positives = 0
        running_positives = 0
        for inputs, classes in dataloader:
            inputs = inputs.to(device)
            classes = classes.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, classes)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            _, preds = torch.max(outputs.data, 1)
            # statistics
            running_loss += loss.data.item()
            running_corrects += torch.sum(preds == classes.data)
            running_true_positives += torch.sum((classes.data == 1) & (preds == classes.data))
            running_positives += torch.sum(classes.data == 1)
        epoch_loss = running_loss / size
        epoch_acc = running_corrects.data.item() / size
        epoch_recall = running_true_positives.to('cpu').numpy() / running_positives.to('cpu').numpy()
        print('Loss: {:.4f} Acc: {:.4f} Recall: {:.4f}'.format(
            epoch_loss, epoch_acc, epoch_recall))
        loss_list.append(epoch_loss)
        acc_list.append(epoch_acc)
        recall_list.append(epoch_recall)
    training_visualisation(loss_list, acc_list, recall_list)

def multi_plots(loss_list, recall_list):
    plt.plot(loss_list)
    plt.plot(recall_list)

def validation_model(model, dataloader, size, criterion):
    '''
    Computes loss and accuracy on validation test

    :param model: neural network model
    :param dataloader: test loader
    :param size: number of images in the dataset
    :return: predictions, probabilities and classes for the validation set
    '''
    model.eval()

    predictions = np.zeros(size)
    all_classes = np.zeros(size)
    all_proba = np.zeros((size, 2))
    i = 0
    running_loss = 0.0
    running_corrects = 0
    running_true_positives = 0
    running_positives = 0
    for inputs, classes in dataloader:
        inputs = inputs.to(device)
        classes = classes.to(device)
        outputs = model(inputs)
        loss = criterion(outputs, classes)
        _, preds = torch.max(outputs.data, 1)
        # statistics
        running_loss += loss.data.item()
        running_corrects += torch.sum(preds == classes.data)
        running_true_positives += torch.sum((classes.data == 1) & (preds == classes.data))
        running_positives += torch.sum(classes.data == 1)
        predictions[i:i+len(classes)] = preds.to('cpu').numpy()
        all_classes[i:i+len(classes)] = classes.to('cpu').numpy()
        all_proba[i:i+len(classes), :] = outputs.data.to('cpu').numpy()
        i += len(classes)
    epoch_loss = running_loss / size
    epoch_acc = running_corrects.data.item() / size
    epoch_recall = running_true_positives.to('cpu').numpy() / running_positives.to('cpu').numpy()
    print('Loss: {:.4f} Acc: {:.4f} Recall: {:.4f}'.format(
                     epoch_loss, epoch_acc, epoch_recall))
    return predictions, all_proba, all_classes


def validation_model_preconvfeat(model, batch_size_train, batch_size_val, shuffle_train, shuffle_valid, num_workers, optim = None, criterion=None):
    '''
    Computes predictions, probabilities and classes for validation set with precomputed extracted features

    :param model: neural network model
    :param batch_size_train: how many samples per batch to load from train set
    :param batch_size_val: how many samples per batch to load from validation set
    :param shuffle_train: set to True to have the train set data reshuffled at every epoch
    :param shuffle_val: set to True to have the validation set data reshuffled at every epoch
    :param batch_size_preconvfeat: how many samples per batch to load from the dataset containing extracted features
    :param num_workers: how many subprocesses to use for data loading
    :return: predictions, probabilities and classes for the validation set
    '''


    train_size, valid_size, loader_train, loader_valid = split_train_valid_sets(batch_size_train,
                                                                                batch_size_val, shuffle_train,
                                                                                shuffle_valid, num_workers)

    '''
    loaderfeat_train = create_preconvfeat_loader(loader_train, model, batch_size_preconvfeat, shuffle_train)
    loaderfeat_valid = create_preconvfeat_loader(loader_valid, model, batch_size_preconvfeat, shuffle_valid)
    '''

    train_model(model, dataloader=loader_train, size=train_size, epochs=num_epochs, optimizer= optim, criterion=criterion)


    predictions, all_proba, all_classes = validation_model(model, dataloader=loader_valid, size= valid_size, criterion=criterion)


    return predictions, all_proba, all_classes

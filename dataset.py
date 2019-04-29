from torch.utils.data import Dataset
import csv
from nltk.tokenize import word_tokenize
import torch


def compute_vocab(csv_file, dst_file, tokenizer=str.split, max_size=None):

    # load csv
    with open(csv_file, 'r') as csvf:
        csv_reader = csv.reader(csvf, delimiter=',')
        rows = list(csv_reader)

    # compute vocab
    all_words = [token for row in rows for token in map(lambda x: x.lower(), tokenizer(row[1]))]
    occurrences = dict()
    for word in all_words:
        occurrences[word] = occurrences.get(word, 0) + 1
    if max_size is None:
        max_size = len(occurrences)

    vocab = set(map(lambda x: x[0], sorted(occurrences.items(), key=lambda x: x[1], reverse=True)[:max_size - 1]))
    vocab.add('<PAD>')
    vocab.add('<UNK>')
    vocab = LabelIndexMap(vocab, required_mappings={'<PAD>': 0, '<UNK>': 1})

    # save vocab
    with open(dst_file, 'w') as f:
        for label, index in vocab.label_to_index.items():
            f.write("{} {}\n".format(label, index))


class LabelIndexMap(object):
    """
    Class used to remap N labels from cluttered, arbitrary values to non-negative, contiguous values in range [0, N-1].
    """

    def __init__(self, all_labels, sort_key=None, required_mappings=None):
        assert (sort_key is None or required_mappings is None), "use only one among sort_key, predefined_positions"
        self.individual_labels = list(set(all_labels))
        if sort_key is not None:
            self.individual_labels = sorted(all_labels, key=sort_key)
        if required_mappings is not None:
            # set items to the required positions
            for element, required_position in required_mappings.items():
                if required_position >= len(self.individual_labels):
                    raise ValueError("Required position is out of range")
                if required_mappings.get(self.individual_labels[required_position], None) == required_position \
                        and element != self.individual_labels[required_position]:
                    raise ValueError("Incompatible required mapping: "
                                     "label '{}' and '{}' both required "
                                     "in position {}".format(element, self.individual_labels[required_position],
                                                             required_position))

                # swap
                current_position = self.individual_labels.index(element)
                self.individual_labels[current_position] = self.individual_labels[required_position]
                self.individual_labels[required_position] = element

        self.label_to_index = {label: i for i, label in enumerate(self.individual_labels)}
        self.index_to_label = {i: label for i, label in enumerate(self.individual_labels)}

    def __getitem__(self, item):
        return self.label_to_index[item]

    def __len__(self):
        return len(self.label_to_index)

    def save(self, filename):
        with open(filename, "w") as f:
            for item in self.label_to_index.items():
                f.write("{}\t{}\n".format(*item))

    @staticmethod
    def load(filename):
        v = dict()
        with open(filename, "r") as f:
            for row in f:
                label, index = row.split()
                v[label] = int(index)
        return LabelIndexMap(v.keys(), required_mappings=v)


class ToxicCommentDataset(Dataset):

    def __init__(self, rows: list, vocab: LabelIndexMap):
        # init
        self.rows = rows
        self.vocab = vocab

    def __getitem__(self, index):
        row = self.rows[index]
        text, classes = row[1], [float(x) for x in row[2:8]]
        tokens = [self.vocab.label_to_index.get(token.lower(), self.vocab.label_to_index['<UNK>'])
                  for token in word_tokenize(text)]
        tokens, classes = torch.tensor(tokens), torch.tensor(classes)
        return tokens, classes

    def __len__(self):
        return len(self.rows)


def produce_datasets(csv_file, vocab, val_ratio=0.2):

    # load csv
    print("Loading CSV file '{}'...".format(csv_file))
    with open(csv_file, 'r') as csvf:
        csv_reader = csv.reader(csvf, delimiter=',')
        rows = list(csv_reader)[1:]

    # load vocab
    if isinstance(vocab, str):
        print("Loading vocab file '{}'...".format(vocab))
        vocab = LabelIndexMap.load(vocab)
    elif not isinstance(vocab, LabelIndexMap):
        raise ValueError("vocab must be str or LabelIndexMap")

    train_size = int((1 - val_ratio) * len(rows))
    train_set, val_set = ToxicCommentDataset(rows[:train_size], vocab), ToxicCommentDataset(rows[train_size:], vocab)
    return train_set, val_set


if __name__ == '__main__':
    ds_train, ds_val = produce_datasets('jigsaw-toxic-comment-classification-challenge/train.csv',
                                        'jigsaw-toxic-comment-classification-challenge/vocab.txt')
    print(len(ds_train))
    print(len(ds_train.vocab))
    print(ds_train[34])
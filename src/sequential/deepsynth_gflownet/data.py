import src.sequential.deepsynth.dsl as dsl
from src.sequential.deepsynth.DSL.list import semantics, primitive_types
from src.sequential.deepsynth.Predictions.dataset_sampler import Dataset
from src.sequential.deepsynth.type_system import *
from src.sequential.deepsynth.model_loader import build_dreamcoder_intlist_model
from src.sequential.deepsynth.dreamcoder_dataset_loader import load_tasks, filter_tasks_for_model
from src.sequential.deepsynth_gflownet.config import *
import torch
from dataclasses import dataclass
import random


@dataclass
class Data:
    device: torch
    data_generator = None
    task_generator = None

    def __post_init__(self):

        self.type_request = Arrow(List(INT), List(INT))
        self.dsl = dsl.DSL(semantics, primitive_types)
        self.cfg = self.dsl.DSL_to_CFG(
            self.type_request,
            max_program_depth=4  # NOTE: this may need to be increased (perhaps gradually)
            )

        self.nb_examples_max = 15
        self.size_max = 10
        nb_arguments_max = 1
        self.lexicon = [x for x in range(-30, 30)]

    # DreamCoder tasks for model evaluation
    @staticmethod
    def load_dreamcoder_tasks():
        folder = DREAMCODER_DATASET_PATH
        tasks = load_tasks(folder)
        print("Loaded", len(tasks), "tasks")
        _, _, rules_predictor = build_dreamcoder_intlist_model(max_program_depth=4)  # NOTE: tasks might need deeper programs (in DeepSynth they use depth=6)
        tasks = filter_tasks_for_model(tasks, rules_predictor)
        print("Remaining tasks after filter:", len(tasks), "tasks")
        dataset_size = len(tasks)

        all_tasks = []
        for name, examples in tasks:
            ex = [([i[0]], o) for i, o in examples]  # Get rid of None in the 'constant' slot (done by i[0])
            all_tasks.append((name, ex))
        return all_tasks, dataset_size

    @staticmethod
    def make_dreamcoder_task_generator(tasks, shuffle=False):
        while True:
            if shuffle:
                random.shuffle(tasks)
            for i in range(len(tasks)):
                yield tasks[i]

    def create_train_dataset(self, max_program_depth, dataset_size):
        cfg = self.dsl.DSL_to_CFG(self.type_request, max_program_depth=max_program_depth)
        self.dataset = Dataset(
            size=dataset_size,
            dsl=self.dsl,
            # TODO: This should be changed to the actual generative model instead of uniform ↓?
            pcfg_dict={self.type_request: cfg.CFG_to_Uniform_PCFG()},
            nb_examples_max=self.nb_examples_max,
            arguments={self.type_request: self.type_request.arguments()},
            ProgramEncoder=lambda x: x,
            size_max=self.size_max,
            lexicon=self.lexicon,
            for_flashfill=False
            )
        self.data_generator = self.dataset.__iter__()

    def get_next_batch(self, batch_size, data_type='train', max_program_depth=4, shuffle=False):

        batch_IOs, batch_program = [], []

        if data_type == 'train':
            # if self.data_generator is None:
            self.create_train_dataset(max_program_depth, batch_size)
            for _ in range(batch_size):
                io, prog, _, _ = next(self.data_generator)
                batch_IOs.append(io)
                batch_program.append(prog)
            return batch_IOs, batch_program

        elif data_type == 'test':
            if self.task_generator is None:
                tasks, self.dataset_size = self.load_dreamcoder_tasks()
                self.task_generator = self.make_dreamcoder_task_generator(tasks, shuffle=shuffle)
            task = next(
                self.task_generator)  # NOTE: This should be moved two rows down if you want different tasks for every batch
            batch_program_names = []
            for i in range(batch_size):
                name, ios = task[0], task[1]
                batch_program_names.append(name)
                batch_IOs.append(ios)
            return batch_IOs, batch_program_names
        else:
            raise ValueError("Invalid data_type. Choose either 'train' or 'test'.")

import torch
import torch.nn as nn
from flowcoder.utils import PositionalEncoding
from flowcoder.config import device

class GFlowNet(nn.Module):
    def __init__(self, cfg, io_encoder, state_encoder, d_model=512, num_heads=8, num_layers=2, dropout=0.1):
        super(GFlowNet, self).__init__()
        self.cfg = cfg
        self.io_encoder = io_encoder
        self.state_encoder = state_encoder
        self.positional_encoding = PositionalEncoding(d_model)

        # Defining the transformer (generative model)
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=num_heads,
            num_encoder_layers=num_layers,
            num_decoder_layers=num_layers,
            dropout=dropout
            )

        # MLPs for logits and logZ
        self.forward_logits = GFlowNet_Forward(d_model, len(state_encoder.rules))

        # self.logZ = self.forward_logits.logZ
        self.logZ = GFlowNet_Z(d_model)  # LogZ measures the partition function

    def forward(self, state, io):

        # TODO: The IO stays the same for the whole duration of the trajectory.
        #  We mustn't recompute it every time

        # Process IO
        io = self.io_encoder(io)
        io = self.positional_encoding(io)

        # Process state
        state = self.state_encoder(state)
        state = self.positional_encoding(state)

        # Generate mask
        mask = self.generate_square_subsequent_mask(len(state))

        # Pass through the transformer
        transformer_output = self.transformer(io, state, tgt_mask=mask)

        # Predict the forward logits and total flow logZ
        forward_logits = self.forward_logits(transformer_output)[-1]
        logZ = self.logZ(transformer_output)[-1]

        return forward_logits, logZ

    def generate_square_subsequent_mask(self, sz):
        mask = (torch.triu(torch.ones(sz, sz)) == 1).transpose(0, 1)
        mask = mask.float().masked_fill(mask == 0, float('-inf')).masked_fill(mask == 1, float(0.0))
        return mask.to(device)


# Forward policy
class GFlowNet_Forward(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(GFlowNet_Forward, self).__init__()
        self.forward_logits = nn.Sequential(
                    nn.LayerNorm(input_dim),
                    nn.Linear(input_dim, input_dim),
                    nn.ReLU(),
                    nn.Linear(input_dim, output_dim)
                )

    def forward(self, x):
        return self.forward_logits(x)


# Partition function
class GFlowNet_Z(nn.Module):
    def __init__(self, d_model):
        super(GFlowNet_Z, self).__init__()
        self.logZ = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, 1)
            )

    def forward(self, x):
        return self.logZ(x)
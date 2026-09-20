"""Deliberately shifted evaluation conditions.

The rubric scores 'robustness to unseen conditions' (lighting / orientation /
batch change). None of that exists in the provided data, so we synthesise the
shifts at eval time and report accuracy per condition. Shifts are applied to
the held-out test split only -- never seen during training.

Every transform here is a module-level class rather than a lambda or closure:
Windows DataLoader workers spawn rather than fork, so the transform must be
picklable or the sweep dies after training completes.
"""

from PIL import Image, ImageEnhance, ImageFilter
from torchvision import transforms

from ai.data import IMAGENET_MEAN, IMAGENET_STD


class Brightness:
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, im):
        return ImageEnhance.Brightness(im).enhance(self.factor)


class Contrast:
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, im):
        return ImageEnhance.Contrast(im).enhance(self.factor)


class Blur:
    def __init__(self, radius):
        self.radius = radius

    def __call__(self, im):
        return im.filter(ImageFilter.GaussianBlur(self.radius))


class Rotate:
    def __init__(self, degrees):
        self.degrees = degrees

    def __call__(self, im):
        return im.rotate(self.degrees, resample=Image.BILINEAR, fillcolor=0)


class Identity:
    def __call__(self, im):
        return im


class Chain:
    def __init__(self, *steps):
        self.steps = steps

    def __call__(self, im):
        for step in self.steps:
            im = step(im)
        return im


# Each entry is a named, physically-motivated shift a real line would produce.
CONDITIONS = {
    "clean": Identity(),
    "bright_lighting": Brightness(1.45),
    "dim_lighting": Brightness(0.6),
    "low_contrast": Contrast(0.55),
    "rotated_15deg": Rotate(15),
    "rotated_90deg": Rotate(90),
    "defocus_blur": Blur(1.6),
    "combined_hard": Chain(Brightness(1.3), Contrast(0.7), Rotate(12), Blur(1.0)),
}


def build_condition_transform(condition: str, img_size: int = 224):
    if condition not in CONDITIONS:
        raise KeyError(f"unknown condition {condition!r}; have {list(CONDITIONS)}")
    return transforms.Compose([
        transforms.Grayscale(num_output_channels=3),
        transforms.Lambda(CONDITIONS[condition]),
        transforms.Resize(img_size + 32),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

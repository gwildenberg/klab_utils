import os
import argparse
import glob 
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
from tqdm import tqdm
from mpi4py import MPI
mpi_comm = MPI.COMM_WORLD
mpi_rank = mpi_comm.Get_rank()
mpi_size = mpi_comm.Get_size()

def gen_mask(img, l_thresh, h_thresh, kernel_size, var_size, var_thresh):
  kernel = np.ones((kernel_size,kernel_size),np.uint8)
  mask = 255*(np.logical_or(img < l_thresh,img > h_thresh)).astype(np.uint8)
  mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
  # mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
  mask = cv2.dilate(mask,kernel,iterations = 4)

  blur_img = cv2.blur(np.float32(img), (var_size, var_size))
  blur_img_2 = cv2.blur(np.square(np.float32(img)), (var_size, var_size))
  var_img = np.sqrt(blur_img_2 - np.square(blur_img))
  mask_2 = 255*(var_img < var_thresh).astype(np.uint8)
  mask_2 = cv2.dilate(mask_2, kernel, iterations=4)

  mask_3 = np.maximum(mask, mask_2)
  mask_3 = 255 - mask_3

  return mask_3


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--image_dir', default=None, type=str)
  parser.add_argument('--mask_dir', default='masks', type=str)
  parser.add_argument('--low', default=5, type=int)
  parser.add_argument('--high', default=250, type=int)
  parser.add_argument('--kernel', default=10, type=int)
  parser.add_argument('--var_size', default=12, type=int)
  parser.add_argument('--var_thresh', default=25, type=int)
  args = parser.parse_args()

  if mpi_rank == 0:
    os.makedirs(args.mask_dir, exist_ok=True)
    f_list = glob.glob(os.path.join(args.image_dir, '*.*'))
    f_list.sort()
    f_sublist = np.array_split(np.asarray(f_list), mpi_size)
  else:
    f_sublist = None
  f_sublist = mpi_comm.scatter(f_sublist, 0)


  for f in tqdm(f_sublist):
    bname = os.path.basename(f).split('.')[0]
    f_mask = os.path.join(args.mask_dir, bname+'.pbm')
    img = cv2.imread(f, 0)
    mask = gen_mask(img, args.low, args.high, args.kernel, args.var_size, args.var_thresh)
    with open(f_mask, 'wb') as fd:
      row, col = mask.shape
      fd.write(bytearray("P4\n%i %i\n" % (col, row), 'ascii'))
      fd.write(np.packbits(mask[:row,:col], axis=-1).tobytes())


if __name__ == '__main__':
  main()

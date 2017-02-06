# Neural-Artistic-Style-Video-
Implementation of Neural Style Transfer on Video.

![](https://github.com/feziodoshi/Neural-Artistic-Style-Video-/blob/master/video/neural_style_1.gif)

Contributers : [Fenil Doshi](), [Raghav Gupta](https://github.com/BeasT321), [Rohan Pooniwala](), [Raghav Gupta]()

# Neural Artistic Style Implementation

We mainly used the following research papers to implament Neural Artistic Style

<ul>
<li>Implementation of Neural Style Transfer from the paper <a href="http://arxiv.org/abs/1508.06576">A Neural Algorithm of Artistic Style</a> in Keras 1.2.0

<li>Color Preservation is based on the paper [Preserving Color in Neural Artistic Style Transfer](https://arxiv.org/abs/1606.05897).

<li>Masked Style Transfer is based on the paper [Show, Divide and Neural: Weighted Style Transfer](http://cs231n.stanford.edu/reports2016/208_Report.pdf)
</ul>

And also took help from the repository [Neural-Style-Transfer](https://github.com/titu1994/Neural-Style-Transfer/) 

# Guide

We are using Keras 1.2.1 with Tensorflow backend Using CUDA on Windows 10. But it should work in Linux with/without CUDA using same keras version.

There are 3 files:
<ul>
<li>
</ul>

# Speed
On a 1070 Laptop GPU, the time required for each epoch depends on mainly image size (gram matrix size) :

For a 400x400 gram matrix, each epoch takes approximately 7-9 seconds. 
For a 512x512 gram matrix, each epoch takes approximately - seconds. 
For a 600x600 gram matrix, each epoch takes approximately - seconds. 

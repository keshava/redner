import tensorflow as tf
tf.enable_eager_execution()
tfe = tf.contrib.eager

import pyrednertensorflow as pyredner
import numpy as np

# Optimize four vertices of a textured patch

# Use GPU if available
pyredner.set_use_gpu(False)

# Set up the scene using Pytorch tensor
position = tfe.Variable([0.0, 0.0, -5.0], dtype=tf.float32)
look_at = tfe.Variable([0.0, 0.0, 0.0], dtype=tf.float32)
up = tfe.Variable([0.0, 1.0, 0.0], dtype=tf.float32)
fov = tfe.Variable([45.0], dtype=tf.float32)
clip_near = 1e-2

resolution = (256, 256)
cam = pyredner.Camera(position = position,
                     look_at = look_at,
                     up = up,
                     fov = fov,
                     clip_near = clip_near,
                     resolution = resolution)

checkerboard_texture = pyredner.imread('checkerboard.exr')
if pyredner.get_use_gpu():
	checkerboard_texture = checkerboard_texture.cuda()

mat_checkerboard = pyredner.Material(
    diffuse_reflectance = checkerboard_texture)
mat_black = pyredner.Material(
    diffuse_reflectance = tfe.Variable([0.0, 0.0, 0.0],
    ))
materials = [mat_checkerboard, mat_black]
vertices = tfe.Variable([[-1.0,-1.0,0.0], [-1.0,1.0,0.0], [1.0,-1.0,0.0], [1.0,1.0,0.0]],
                        )
indices = tfe.Variable([[0, 1, 2], [1, 3, 2]], dtype=tf.int32,
                       )
uvs = tfe.Variable([[0.05, 0.05], [0.05, 0.95], [0.95, 0.05], [0.95, 0.95]],
				   )
shape_plane = pyredner.Shape(vertices, indices, uvs, None, 0)
light_vertices = tfe.Variable([[-1.0,-1.0,-7.0],[1.0,-1.0,-7.0],[-1.0,1.0,-7.0],[1.0,1.0,-7.0]],
                              )
light_indices = tfe.Variable([[0,1,2],[1,3,2]], dtype=tf.int32, )
shape_light = pyredner.Shape(light_vertices, light_indices, None, None, 1)
shapes = [shape_plane, shape_light]
light_intensity = tfe.Variable([20.0, 20.0, 20.0])
# The first argument is the shape id of the light
light = pyredner.AreaLight(1, light_intensity)
area_lights = [light]
scene = pyredner.Scene(cam, shapes, materials, area_lights)
scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 16,
    max_bounces = 1)

# Alias of the render function

# Render our target
img = pyredner.render(0, *scene_args)
pyredner.imwrite(img, 'results/test_texture/target.exr')
pyredner.imwrite(img, 'results/test_texture/target.png')
target = pyredner.imread('results/test_texture/target.exr')

# Perturb the scene, this is our initial guess
shape_plane.vertices = tfe.Variable(
    [[-1.1,-1.2,0.0], [-1.3,1.1,0.0], [1.1,-1.1,0.0], [0.8,1.2,0.0]],
    dtype=tf.float32,
    trainable=True)
scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 16,
    max_bounces = 1)
# Render the initial guess
img = pyredner.render(1, *scene_args)
pyredner.imwrite(img, 'results/test_texture/init.png')
diff = tf.abs(target - img)
pyredner.imwrite(diff, 'results/test_texture/init_diff.png')

# Optimize for triangle vertices
# optimizer = torch.optim.Adam([shape_plane.vertices], lr=5e-2)
optimizer = tf.train.AdamOptimizer(5e-2)

scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 4,
    max_bounces = 1)
for t in range(200):
    print('iteration:', t)

    with tf.GradientTape() as tape:
        img = pyredner.render(t+1, *scene_args)
        
        # Forward pass: render the image
        pyredner.imwrite(img, 'results/test_texture/iter_{}.png'.format(t))
        loss = tf.reduce_sum(tf.square(img - target))
    
    print('loss:', loss)

    grads = tape.gradient(loss, [shape_plane.vertices])
    optimizer.apply_gradients(
        zip(grads, [shape_plane.vertices])
        )

    print('grad:', grads)
    print('vertices:', shape_plane.vertices)

scene_args = pyredner.serialize_scene(
    scene = scene,
    num_samples = 16,
    max_bounces = 1)
img = pyredner.render(202, *scene_args)
pyredner.imwrite(img, 'results/test_texture/final.exr')
pyredner.imwrite(img, 'results/test_texture/final.png')
pyredner.imwrite(tf.abs(target - img).cpu(), 'results/test_texture/final_diff.png')

from subprocess import call
call(["ffmpeg", "-framerate", "24", "-i",
    "results/test_texture/iter_%d.png", "-vb", "20M",
    "results/test_texture/out.mp4"])

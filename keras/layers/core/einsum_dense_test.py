import os

import numpy as np
import pytest
from absl.testing import parameterized

from keras import backend
from keras import constraints
from keras import layers
from keras import models
from keras import ops
from keras import saving
from keras import testing
from keras.export import export_lib


class EinsumDenseTest(testing.TestCase, parameterized.TestCase):
    @parameterized.named_parameters(
        {
            "testcase_name": "_1d_end_weight",
            "equation": "ab,b->a",
            "bias_axes": None,
            "input_shape": (2, 32),
            "output_shape": (),
            "expected_kernel_shape": (32,),
            "expected_bias_shape": None,
            "expected_output_shape": (2,),
        },
        {
            "testcase_name": "_2d_middle_weight",
            "equation": "ab,bc->ac",
            "bias_axes": None,
            "input_shape": (2, 32),
            "output_shape": (64),
            "expected_kernel_shape": (32, 64),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 64),
        },
        {
            "testcase_name": "_3d_bert",
            "equation": "abc,cde->abde",
            "bias_axes": None,
            "input_shape": (2, 1, 2),
            "output_shape": (1, 3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_3d_3_bias",
            "equation": "abc,cde->abde",
            "bias_axes": "e",
            "input_shape": (2, 1, 2),
            "output_shape": (1, 3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": (4,),
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_3d_2_bias",
            "equation": "abc,cde->abde",
            "bias_axes": "d",
            "input_shape": (2, 1, 2),
            "output_shape": (1, 3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": (3, 1),
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_3d_1_3_bias",
            "equation": "abc,cde->abde",
            "bias_axes": "be",
            "input_shape": (2, 7, 2),
            "output_shape": (7, 3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": (7, 1, 4),
            "expected_output_shape": (2, 7, 3, 4),
        },
        {
            "testcase_name": "_3d_bert_projection",
            "equation": "BFNH,NHD->BFD",
            "bias_axes": None,
            "input_shape": (2, 1, 2, 3),
            "output_shape": (1, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 1, 4),
        },
        {
            "testcase_name": "_2d_bert",
            "equation": "abc,cd->abd",
            "bias_axes": None,
            "input_shape": (2, 1, 2),
            "output_shape": (1, 4),
            "expected_kernel_shape": (2, 4),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 1, 4),
        },
        {
            "testcase_name": "_embedding_1d",
            "equation": "i,d->id",
            "bias_axes": None,
            "input_shape": (2,),
            "output_shape": (2,),
            "expected_kernel_shape": (2,),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 2),
        },
        {
            "testcase_name": "_xlnet_lm",
            "equation": "ibd,nd->ibn",
            "bias_axes": None,
            "input_shape": (2, 2, 1),
            "output_shape": (2, 2),
            "expected_kernel_shape": (2, 1),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 2, 2),
        },
        {
            "testcase_name": "_2d_precast",
            "equation": "...b,bc->...c",
            "bias_axes": None,
            "input_shape": (2, 32),
            "output_shape": (64,),
            "expected_kernel_shape": (32, 64),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 64),
        },
        {
            "testcase_name": "_2d_precast_elided_input_used_in_output",
            "equation": "...bc,bc->...b",
            "bias_axes": None,
            "input_shape": (2, 32, 64),
            "output_shape": (32,),
            "expected_kernel_shape": (32, 64),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 32),
        },
        {
            "testcase_name": "_2d_precast_multiple_elided_dims",
            "equation": "...b,bc->...c",
            "bias_axes": None,
            "input_shape": (2, 3, 32),
            "output_shape": (64,),
            "expected_kernel_shape": (32, 64),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 3, 64),
        },
        {
            "testcase_name": "_3d_precast",
            "equation": "...c,cde->...de",
            "bias_axes": None,
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_3d_precast_3_bias",
            "equation": "...c,cde->...de",
            "bias_axes": "e",
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": (4,),
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_3d_precast_2_bias",
            "equation": "...c,cde->...de",
            "bias_axes": "d",
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": (3, 1),
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_3d_precast_2_3_bias",
            "equation": "...c,cde->...de",
            "bias_axes": "de",
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (2, 3, 4),
            "expected_bias_shape": (3, 4),
            "expected_output_shape": (2, 1, 3, 4),
        },
        {
            "testcase_name": "_2d_postcast",
            "equation": "bc...,cd->bd...",
            "bias_axes": None,
            "input_shape": (2, 1, 2, 3),
            "output_shape": (4,),
            "expected_kernel_shape": (1, 4),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 4, 2, 3),
        },
        {
            "testcase_name": "_3d_postcast",
            "equation": "bc...,cde->bde...",
            "bias_axes": None,
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (1, 3, 4),
            "expected_bias_shape": None,
            "expected_output_shape": (2, 3, 4, 2),
        },
        {
            "testcase_name": "_3d_postcast_1_bias",
            "equation": "bc...,cde->bde...",
            "bias_axes": "d",
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (1, 3, 4),
            "expected_bias_shape": (3, 1, 1),
            "expected_output_shape": (2, 3, 4, 2),
        },
        {
            "testcase_name": "_3d_postcast_2_bias",
            "equation": "bc...,cde->bde...",
            "bias_axes": "e",
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (1, 3, 4),
            "expected_bias_shape": (4, 1),
            "expected_output_shape": (2, 3, 4, 2),
        },
        {
            "testcase_name": "_3d_postcast_1_2_bias",
            "equation": "bc...,cde->bde...",
            "bias_axes": "de",
            "input_shape": (2, 1, 2),
            "output_shape": (3, 4),
            "expected_kernel_shape": (1, 3, 4),
            "expected_bias_shape": (3, 4, 1),
            "expected_output_shape": (2, 3, 4, 2),
        },
    )
    @pytest.mark.requires_trainable_backend
    def test_einsum_dense_basics(
        self,
        equation,
        bias_axes,
        input_shape,
        output_shape,
        expected_kernel_shape,
        expected_bias_shape,
        expected_output_shape,
    ):
        self.run_layer_test(
            layers.EinsumDense,
            init_kwargs={
                "equation": equation,
                "output_shape": output_shape,
                "bias_axes": bias_axes,
            },
            input_shape=input_shape,
            expected_output_shape=expected_output_shape,
            expected_num_trainable_weights=(
                2 if expected_bias_shape is not None else 1
            ),
            expected_num_non_trainable_weights=0,
            expected_num_seed_generators=0,
            expected_num_losses=0,
            supports_masking=False,
        )
        layer = layers.EinsumDense(
            equation, output_shape=output_shape, bias_axes=bias_axes
        )
        layer.build(input_shape)
        self.assertEqual(layer.kernel.shape, expected_kernel_shape)
        if expected_bias_shape is not None:
            self.assertEqual(layer.bias.shape, expected_bias_shape)

    def test_einsum_dense_constraints(self):
        layer = layers.EinsumDense(
            "abc,cde->abde", (1, 3, 4), kernel_constraint="non_neg"
        )
        layer.build((2, 1, 2))
        self.assertIsInstance(layer.kernel.constraint, constraints.NonNeg)
        layer = layers.EinsumDense(
            "ab,b->a", (1, 3, 4), bias_axes="a", bias_constraint="non_neg"
        )
        layer.build((2, 1, 2))
        self.assertIsInstance(layer.bias.constraint, constraints.NonNeg)

    @pytest.mark.requires_trainable_backend
    def test_enable_lora(self):
        layer = layers.EinsumDense(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes=None,
        )
        layer.build((None, 3))
        layer.enable_lora(2)
        self.assertLen(layer.trainable_weights, 2)
        self.assertLen(layer.non_trainable_weights, 1)
        # Try eager call
        x = np.random.random((64, 3))
        y = np.random.random((64, 8, 32))
        _ = layer(x[:2])

        init_lora_a_kernel_value = layer.lora_kernel_a.numpy()
        init_lora_b_kernel_value = layer.lora_kernel_b.numpy()

        # Try calling fit()
        model = models.Sequential(
            [
                layer,
            ]
        )
        model.compile(optimizer="sgd", loss="mse")
        model.fit(x, y, epochs=2)

        final_lora_a_kernel_value = layer.lora_kernel_a.numpy()
        final_lora_b_kernel_value = layer.lora_kernel_b.numpy()
        diff_a = np.max(np.abs(init_lora_a_kernel_value - final_lora_a_kernel_value))
        diff_b = np.max(np.abs(init_lora_b_kernel_value - final_lora_b_kernel_value))
        self.assertGreater(diff_a, 0.0)
        self.assertGreater(diff_b, 0.0)

        # Try saving and reloading the model
        temp_filepath = os.path.join(self.get_temp_dir(), "lora_model.keras")
        model.save(temp_filepath)

        new_model = saving.load_model(temp_filepath)
        self.assertTrue(new_model.layers[0].lora_enabled)
        self.assertAllClose(model.predict(x), new_model.predict(x))

        # Try saving and reloading the model's weights only
        temp_filepath = os.path.join(self.get_temp_dir(), "lora_model.weights.h5")
        model.save_weights(temp_filepath)

        # Load the file into a fresh, non-lora model
        new_model = models.Sequential(
            [
                layers.EinsumDense(
                    equation="ab,bcd->acd",
                    output_shape=(8, 32),
                    bias_axes=None,
                ),
            ]
        )
        new_model.build((None, 3))
        new_model.load_weights(temp_filepath)
        self.assertAllClose(model.predict(x), new_model.predict(x))

        # Try loading a normal checkpoint into a lora model
        new_model.save_weights(temp_filepath)
        model.load_weights(temp_filepath)
        self.assertAllClose(model.predict(x), new_model.predict(x))

    @pytest.mark.requires_trainable_backend
    def test_lora_rank_argument(self):
        self.run_layer_test(
            layers.EinsumDense,
            init_kwargs={
                "equation": "ab,bcd->acd",
                "output_shape": (8, 32),
                "bias_axes": None,
                "lora_rank": 2,
            },
            input_shape=(2, 3),
            expected_output_shape=(2, 8, 32),
            expected_num_trainable_weights=2,
            expected_num_non_trainable_weights=1,
            expected_num_seed_generators=0,
            expected_num_losses=0,
            supports_masking=False,
        )

    @pytest.mark.skipif(
        backend.backend() == "numpy",
        reason=f"{backend.backend()} does not support ops.custom_gradient.",
    )
    def test_quantize_int8(self):
        layer = layers.EinsumDense(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes="d",
        )
        layer.build((None, 3))
        x = np.random.random((2, 3))
        y_float = layer(x)
        layer.quantize("int8")

        # Verify weights dtype
        self.assertEqual(backend.standardize_dtype(layer._kernel.dtype), "int8")
        self.assertEqual(
            backend.standardize_dtype(layer.kernel_scale.dtype),
            layer.variable_dtype,
        )

        # Try eager call and verify output correctness
        y_quantized = layer(x)
        mse = ops.mean(ops.square(y_float - y_quantized))
        self.assertLess(mse, 1e-3)  # A weak correctness test

        # Try saving and reloading the model
        model = models.Sequential([layer])
        temp_filepath = os.path.join(self.get_temp_dir(), "quantized_model.keras")
        model.save(temp_filepath)
        new_model = saving.load_model(temp_filepath)
        self.assertAllClose(model.predict(x), new_model.predict(x))

        # Try saving and reloading the model's weights only
        temp_filepath = os.path.join(self.get_temp_dir(), "quantized_model.weights.h5")
        model.save_weights(temp_filepath)

        # Try lora
        layer = layers.EinsumDense(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes="d",
        )
        layer.build((None, 3))
        layer.enable_lora(2)
        layer.quantize("int8")
        x = np.random.random((2, 3))
        _ = layer(x)

        # Try building with quantized dtype policy
        layer = layers.EinsumDense(
            equation="abcde,afce->acdbf",  # Test reduce and transpose
            output_shape=(2, 4, 8, 16),
            bias_axes="d",
            dtype="int8_from_mixed_bfloat16",
        )
        layer.build((1, 8, 2, 4, 32))
        self.assertEqual(backend.standardize_dtype(layer._kernel.dtype), "int8")
        self.assertEqual(backend.standardize_dtype(layer.kernel_scale.dtype), "float32")
        layer = layers.EinsumDense(
            equation="a,b->ab",  # Test expand
            output_shape=(4,),
            dtype="int8_from_float32",
        )
        layer.build((None,))
        self.assertEqual(backend.standardize_dtype(layer._kernel.dtype), "int8")
        self.assertEqual(backend.standardize_dtype(layer.kernel_scale.dtype), "float32")
        layer = layers.EinsumDense(
            equation="ab,ab->a",  # Test squeeze
            output_shape=(2,),
            dtype="int8_from_float32",
        )
        layer.build((2, 4))
        self.assertEqual(backend.standardize_dtype(layer._kernel.dtype), "int8")
        self.assertEqual(backend.standardize_dtype(layer.kernel_scale.dtype), "float32")

    @pytest.mark.requires_trainable_backend
    def test_quantize_dtype_argument(self):
        self.run_layer_test(
            layers.EinsumDense,
            init_kwargs={
                "equation": "ab,bcd->acd",
                "output_shape": (8, 32),
                "bias_axes": "d",
                "dtype": "int8_from_mixed_bfloat16",
            },
            input_shape=(2, 3),
            expected_output_shape=(2, 8, 32),
            expected_num_trainable_weights=1,
            expected_num_non_trainable_weights=2,
            expected_num_seed_generators=0,
            expected_num_losses=0,
            supports_masking=False,
        )

    def test_quantize_on_unbuilt_layer(self):
        layer = layers.EinsumDense(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes="d",
        )
        with self.assertRaisesRegex(
            ValueError, "Cannot quantize a layer that isn't yet built."
        ):
            layer.quantize("int8")

    def test_quantize_on_subclass(self):
        class MyEinsumDense(layers.EinsumDense):
            pass

        layer = MyEinsumDense(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes="d",
        )
        layer.build((None, 3))
        with self.assertRaises(NotImplementedError):
            layer.quantize("int8")

    def test_quantize_when_already_quantized(self):
        layer = layers.EinsumDense(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes="d",
        )
        layer.build((None, 3))
        layer.quantize("int8")
        with self.assertRaisesRegex(
            ValueError, "`quantize` can only be done once per layer."
        ):
            layer.quantize("int8")

    @pytest.mark.requires_trainable_backend
    def test_quantize_when_lora_enabled(self):
        config = dict(
            equation="ab,bcd->acd",
            output_shape=(8, 32),
            bias_axes=None,
        )
        layer = layers.EinsumDense(**config)
        layer.build((None, 3))
        layer.enable_lora(2)
        layer.quantize("int8")
        self.assertLen(layer.trainable_weights, 2)
        self.assertLen(layer.non_trainable_weights, 2)

        # Try calling fit()
        init_lora_a_kernel_value = layer.lora_kernel_a.numpy()
        init_lora_b_kernel_value = layer.lora_kernel_b.numpy()
        x = np.random.random((64, 3))
        y = np.random.random((64, 8, 32))
        model = models.Sequential([layer])
        model.compile(optimizer="sgd", loss="mse")
        model.fit(x, y, epochs=2)

        final_lora_a_kernel_value = layer.lora_kernel_a.numpy()
        final_lora_b_kernel_value = layer.lora_kernel_b.numpy()
        diff_a = np.max(np.abs(init_lora_a_kernel_value - final_lora_a_kernel_value))
        diff_b = np.max(np.abs(init_lora_b_kernel_value - final_lora_b_kernel_value))
        self.assertGreater(diff_a, 0.0)
        self.assertGreater(diff_b, 0.0)

        # Try saving and reloading the model
        temp_filepath = os.path.join(self.get_temp_dir(), "quantized_lora_model.keras")
        model.save(temp_filepath)
        new_model = saving.load_model(temp_filepath)
        self.assertTrue(new_model.layers[0].lora_enabled)
        self.assertAllClose(model.predict(x), new_model.predict(x), atol=0.5)

        # Try saving and reloading the model's weights only
        temp_filepath = os.path.join(
            self.get_temp_dir(), "quantized_lora_model.weights.h5"
        )
        model.save_weights(temp_filepath)
        new_model = models.Sequential([layers.EinsumDense(**config)])
        new_model.build((None, 3))
        new_model.quantize("int8")
        new_model.load_weights(temp_filepath)
        self.assertFalse(new_model.layers[0].lora_enabled)
        self.assertAllClose(model.predict(x), new_model.predict(x), atol=0.5)

        # Try loading a normal checkpoint into a lora model
        new_model.save_weights(temp_filepath)
        model.load_weights(temp_filepath)
        self.assertAllClose(model.predict(x), new_model.predict(x), atol=0.5)

        # Test export and TFSMLayer reloading when using tensorflow backend
        if backend.backend() == "tensorflow":
            import tensorflow as tf

            temp_filepath = os.path.join(self.get_temp_dir(), "exported_model")
            ref_input = tf.random.normal((32, 3))
            ref_output = model(ref_input)
            export_lib.export_model(model, temp_filepath)
            reloaded_layer = export_lib.TFSMLayer(temp_filepath)
            self.assertAllClose(reloaded_layer(ref_input), ref_output, atol=1e-7)
            self.assertLen(reloaded_layer.weights, len(model.weights))
            self.assertLen(
                reloaded_layer.trainable_weights, len(model.trainable_weights)
            )
            self.assertLen(
                reloaded_layer.non_trainable_weights,
                len(model.non_trainable_weights),
            )

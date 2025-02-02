# Copyright 2021 The NetKet Authors - All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import jax
import netket as nk
import numpy as np
import pytest
from flax.core import freeze
from jax import numpy as jnp


@pytest.mark.parametrize("dtype", [jnp.float64, jnp.complex128])
@pytest.mark.parametrize(
    "hilbert",
    [
        pytest.param(
            nk.hilbert.Spin(s=1 / 2, N=4),
            id="spin_1/2",
        ),
        pytest.param(
            nk.hilbert.Spin(s=1, N=4),
            id="spin_1",
        ),
        pytest.param(
            nk.hilbert.Fock(n_max=3, N=4),
            id="fock",
        ),
    ],
)
@pytest.mark.parametrize(
    "partial_model",
    [
        pytest.param(
            lambda hilbert, dtype: nk.models.ARNNDense(
                hilbert=hilbert,
                layers=3,
                features=5,
                dtype=dtype,
            ),
            id="dense",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.ARNNConv1D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=2,
                dtype=dtype,
            ),
            id="conv1d",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.ARNNConv1D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=2,
                kernel_dilation=2,
                dtype=dtype,
            ),
            id="conv1d_dilation",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.ARNNConv2D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=(2, 3),
                dtype=dtype,
            ),
            id="conv2d",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.ARNNConv2D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=(2, 3),
                kernel_dilation=(2, 2),
                dtype=dtype,
            ),
            id="conv2d_dilation",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.FastARNNDense(
                hilbert=hilbert,
                layers=3,
                features=5,
                dtype=dtype,
            ),
            id="fast_dense",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.FastARNNConv1D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=2,
                dtype=dtype,
            ),
            id="fast_conv1d",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.FastARNNConv1D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=2,
                kernel_dilation=2,
                dtype=dtype,
            ),
            id="fast_conv1d_dilation",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.FastARNNConv2D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=(2, 3),
                dtype=dtype,
            ),
            id="fast_conv2d",
        ),
        pytest.param(
            lambda hilbert, dtype: nk.models.FastARNNConv2D(
                hilbert=hilbert,
                layers=3,
                features=5,
                kernel_size=(2, 3),
                kernel_dilation=(2, 2),
                dtype=dtype,
            ),
            id="fast_conv2d_dilation",
        ),
    ],
)
def test_ARNN(partial_model, hilbert, dtype):
    batch_size = 3

    model = partial_model(hilbert, dtype)

    key_spins, key_model = jax.random.split(jax.random.PRNGKey(0))
    spins = hilbert.random_state(key_spins, size=batch_size)
    p, params = model.init_with_output(key_model, spins, method=model.conditionals)

    # Test if the model is normalized
    # The result may not be very accurate, because it is in exp space
    psi = nk.nn.to_array(hilbert, model.apply, params, normalize=False)
    assert psi.conj() @ psi == pytest.approx(1, rel=1e-5, abs=1e-5)

    # Test if the model is autoregressive
    for i in range(batch_size):
        for j in range(hilbert.size):
            # Change one input element at a time
            spins_new = spins.at[i, j].set(-spins[i, j])
            p_new = model.apply(params, spins_new, method=model.conditionals)

            # Sites after j can change, so we reset them before comparison
            p_new = p_new.at[i, j + 1 :].set(p[i, j + 1 :])

            np.testing.assert_allclose(p_new, p, err_msg=f"i={i} j={j}")


@pytest.mark.parametrize("dtype", [jnp.float64, jnp.complex128])
@pytest.mark.parametrize(
    "hilbert",
    [
        pytest.param(
            nk.hilbert.Spin(s=1 / 2, N=4),
            id="spin_1/2",
        ),
        pytest.param(
            nk.hilbert.Spin(s=1, N=4),
            id="spin_1",
        ),
        pytest.param(
            nk.hilbert.Fock(n_max=3, N=4),
            id="fock",
        ),
    ],
)
@pytest.mark.parametrize(
    "partial_models",
    [
        pytest.param(
            (
                lambda hilbert, dtype: nk.models.ARNNDense(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    dtype=dtype,
                ),
                lambda hilbert, dtype: nk.models.FastARNNDense(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    dtype=dtype,
                ),
            ),
            id="dense",
        ),
        pytest.param(
            (
                lambda hilbert, dtype: nk.models.ARNNConv1D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=2,
                    dtype=dtype,
                ),
                lambda hilbert, dtype: nk.models.FastARNNConv1D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=2,
                    dtype=dtype,
                ),
            ),
            id="conv1d",
        ),
        pytest.param(
            (
                lambda hilbert, dtype: nk.models.ARNNConv1D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=2,
                    kernel_dilation=2,
                    dtype=dtype,
                ),
                lambda hilbert, dtype: nk.models.FastARNNConv1D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=2,
                    kernel_dilation=2,
                    dtype=dtype,
                ),
            ),
            id="conv1d_dilation",
        ),
        pytest.param(
            (
                lambda hilbert, dtype: nk.models.ARNNConv2D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=(2, 3),
                    dtype=dtype,
                ),
                lambda hilbert, dtype: nk.models.FastARNNConv2D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=(2, 3),
                    dtype=dtype,
                ),
            ),
            id="conv2d",
        ),
        pytest.param(
            (
                lambda hilbert, dtype: nk.models.ARNNConv2D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=(2, 3),
                    kernel_dilation=(2, 2),
                    dtype=dtype,
                ),
                lambda hilbert, dtype: nk.models.FastARNNConv2D(
                    hilbert=hilbert,
                    layers=3,
                    features=5,
                    kernel_size=(2, 3),
                    kernel_dilation=(2, 2),
                    dtype=dtype,
                ),
            ),
            id="conv2d_dilation",
        ),
    ],
)
def test_same(partial_models, hilbert, dtype):
    batch_size = 3

    model1 = partial_models[0](hilbert, dtype)
    model2 = partial_models[1](hilbert, dtype)

    key_spins, key_model = jax.random.split(jax.random.PRNGKey(0))
    spins = hilbert.random_state(key_spins, size=batch_size)
    variables = model2.init(key_model, spins, 0, method=model2._conditional)

    p1 = model1.apply(variables, spins, method=model1.conditionals)
    p2 = model2.apply(variables, spins, method=model2.conditionals)

    # Results from `FastARNN*.conditionals` should be the same as those from `ARNN*.conditionals`
    np.testing.assert_allclose(p2, p1)

    p3 = jnp.zeros_like(p1)
    params = variables["params"]
    cache = variables["cache"]
    for i in range(hilbert.size):
        variables = freeze({"params": params, "cache": cache})
        p_i, mutables = model2.apply(
            variables,
            spins,
            i,
            method=model2._conditional,
            mutable=["cache"],
        )
        cache = mutables["cache"]
        p3 = p3.at[:, i, :].set(p_i)

    # Results from `FastARNN*.conditional` should be the same as those from `ARNN*.conditionals`
    np.testing.assert_allclose(p3, p1)


def test_throwing():
    def build_model(hilbert):
        nk.models.ARNNConv1D(hilbert=hilbert, layers=3, features=5, kernel_size=2)

    # Only homogeneous Hilbert spaces are supported
    with pytest.raises(ValueError):
        hilbert = nk.hilbert.Spin(s=1 / 2, N=4)
        hilbert = nk.hilbert.DoubledHilbert(hilbert)
        build_model(None)

    # Only unconstrained Hilbert spaces are supported
    with pytest.raises(ValueError):
        hilbert = nk.hilbert.Fock(n_max=3, N=4, n_particles=3)
        build_model(hilbert)

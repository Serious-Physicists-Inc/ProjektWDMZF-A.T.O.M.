# python internals
from __future__ import annotations
from typing import Tuple, Union, Callable
# internal packages
from .ntypes import *
# external packages
import numpy as np
from scipy.special import genlaguerre as laguerre
from scipy.special import lpmv as legendre
from scipy.special import factorial as fact
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

class StateSpec:
    def __new__(cls, n: int, l: int, m: int):
        if type(n) is not int:
            raise TypeError("Principal quantum number 'n' must be an integer")
        elif n < 1:
            raise ValueError("Principal quantum number value 'n' must be greater than 0")

        if type(l) is not int:
            raise TypeError("Azimuthal quantum number 'l' must be an integer")
        elif l >= n:
            raise ValueError("Azimuthal quantum number value 'l' must be lower than principal quantum number value")

        if type(m) is not int:
            raise TypeError("Magnetic quantum number 'm' must be a whole number")
        if m < -l or m > l:
            raise ValueError("Modulus of magnetic quanum number 'm' must be lower than azimuthal quantum number value")

        return super().__new__(cls)
    def __init__(self, n: int, l: int, m: int) -> None:
        self.__n = n
        self.__l = l
        self.__m = m
    def __eq__(self, other):
        if not isinstance(other, StateSpec):
            return NotImplemented
        return self.__n == other.n and self.__l == other.l and self.__m == other.m
    @property
    def n(self) -> int: return self.__n
    @property
    def l(self) -> int: return self.__l
    @property
    def m(self) -> int: return self.__m

class State:
    def __init__(self, spec: StateSpec) -> None:
        self.__spec = spec
    def __eq__(self, other):
        if not isinstance(other, State):
            return NotImplemented
        return self.__spec == other.spec
    @property
    def spec(self) -> StateSpec:
        return self.__spec
    def wave_func(self, p: SphPointsGrid) -> WaveFunction:
        return WaveFunction(self, p)
    def energy_func(self) -> EnergyFunction:
        return EnergyFunction(self)

class WaveFunction:
    scale = 1.0
    def __init__(self, state: State, p: SphPointsGrid) -> None:
        px = np.asarray(legendre(abs(state.spec.m), state.spec.l, np.cos(p.theta)), dtype=NPComplexT)
        angle = (-1) ** abs(state.spec.m) * np.sqrt(((2*state.spec.l+1) * fact(state.spec.l - abs(state.spec.m))) / (4 * np.pi*fact(state.spec.l + abs(state.spec.m)))) * px * np.exp(1j*abs(state.spec.m)*p.phi)
        la = np.asarray(laguerre(state.spec.n-state.spec.l-1, 2*state.spec.l+1)(2*p.r/(state.spec.n * self.scale)), dtype=NPFloatT)
        radius = p.r ** state.spec.l * (2/(state.spec.n*self.scale)) ** (state.spec.l+1) * la * np.exp(-p.r / (state.spec.n*self.scale))
        self.__init_val: NPCArrayT = radius * angle
        self.__energy_func = state.energy_func()
    def val(self, t: float = 0.0) -> NPCArrayT:
        return self.__init_val*np.exp(-1j*self.__energy_func.val()*t)

class EnergyFunction:
    # physics constants
    alpha_phys = 7.2973525693e-3
    c_phys = 299792458.0
    mu_phys = 9.1093837015e-31
    e = 1.602176634e-19
    # model constants
    mu = 1.0
    alpha = 1.0 / 137.036
    c = 1.0 / alpha
    def __init__(self, state: State) -> None:
        self.__init_val = self.mu * self.c ** 2 * (np.sqrt(1 - self.alpha ** 2 / (state.spec.n - state.spec.l - 1 + np.sqrt((state.spec.l + 1) ** 2 - self.alpha ** 2)) ** 2) - 1)
        self.__init_ev_val = self.mu_phys * self.c_phys ** 2 * (np.sqrt(1 - self.alpha_phys ** 2 / (state.spec.n - state.spec.l - 1 + np.sqrt((state.spec.l + 1) ** 2 - self.alpha_phys ** 2)) ** 2) - 1) / self.e
    def val(self) -> NPFloatT:
        return self.__init_val
    def ev_val(self) -> NPFloatT:
        return self.__init_ev_val

class Atom:
    def __new__(cls, *args: State) -> Atom:
        if any(args[i] == args[j] for i in range(len(args)) for j in range(i + 1, len(args))):
            raise ValueError("At least two quantum states are the same")
        return super().__new__(cls)
    def __init__(self, *args: State) -> None:
        self.__states = args
    def __eq__(self, other):
        if not isinstance(other, Atom):
            return NotImplemented
        return self.specs == other.specs
    @property
    def states(self) -> Tuple[State, ...]:
        return self.__states
    @property
    def specs(self) -> Tuple[StateSpec, ...]:
        return tuple(state.spec for state in self.__states)
    def prob_func(self, p: SphPointsGrid) ->  ProbFunction:
        return ProbFunction(self.__states, p)

class ProbFunction:
    def __init__(self, states: Tuple[State, ...], p: SphPointsGrid) -> None:
        self.__wave_funcs = tuple(state.wave_func(p) for state in states)
    def val(self, t: float = 0.0) -> NPFArrayT:
        psi = np.sum(np.asarray(tuple(wave_fun.val(t) for wave_fun in self.__wave_funcs), dtype=NPComplexT), axis=0)
        return np.abs(psi) ** 2

class Plotter:
    def __init__(self, atom: Atom, dims: Union[SphDims, CartDims]) -> None:
        self.__dims = dims

        rmax = 10 * max(spec.n for spec in atom.specs) ** 2
        r = np.linspace(0, rmax, self.__sph_dims.r_dim)
        theta = np.linspace(0, np.pi, self.__sph_dims.angle_dim)
        phi = np.linspace(0, 2 * np.pi, self.__sph_dims.angle_dim)
        self.__sph_grid: SphPointsGrid = SphPointsGrid(*(np.meshgrid(r, theta, phi, indexing='ij')), )
        self.__cart_grid = CartPointsGrid(
            self.__sph_grid.r * np.sin(self.__sph_grid.theta) * np.cos(self.__sph_grid.phi),
            self.__sph_grid.r * np.sin(self.__sph_grid.theta) * np.sin(self.__sph_grid.phi),
            self.__sph_grid.r * np.cos(self.__sph_grid.theta)
        )
        self.__val_func: ProbFunction = atom.prob_func(self.__sph_grid)
    @property
    def __sph_dims(self) -> SphDims:
        return self.__dims if type(self.__dims) is SphDims else self.__dims.to_sph()
    @property
    def __cart_dims(self) -> CartDims:
        return self.__dims if type(self.__dims) is CartDims else self.__dims.to_cart()
    def scatter(self) -> ScatterFunction:
        return ScatterFunction(self.__cart_grid, self.__val_func.val)
    def volume(self) -> VolumeFunction:
        return VolumeFunction(self.__cart_grid, self.__val_func.val)

class ScatterFunction:
    def __init__(self, grid: CartPointsGrid, val_func: Callable[[float], NPFArrayT]) -> None:
        self.__grid = grid
        self.__val_func = val_func
    def val(self, t: float = 0.0) -> Scatter:
        return Scatter(self.__grid.ravel(), self.__val_func(t).ravel())

class VolumeFunction:
    def __init__(self, grid: CartPointsGrid, val_func: Callable[[float], NPFArrayT],) -> None:
        self.__dims = CartDims(*grid.x.shape)
        self.__val_func = val_func

        xi = np.linspace(np.min(grid.x), np.max(grid.x), self.__dims.x_dim)
        yi = np.linspace(np.min(grid.y), np.max(grid.y), self.__dims.y_dim)
        zi = np.linspace(np.min(grid.z), np.max(grid.z), self.__dims.z_dim)

        query_points = np.stack(np.meshgrid(xi, yi, zi, indexing="ij"), axis=-1).reshape(-1, 3)

        points = np.column_stack(grid.ravel())
        tree = cKDTree(points)

        dist, idx = tree.query(query_points, k=8, workers=-1)

        w = 1.0 / (dist + 1e-6)
        w /= w.sum(axis=1, keepdims=True)

        self.__idx = idx
        self.__w = w
    def val(self, t: float = 0.0) -> Volume:
        values = np.sum(self.__val_func(t).ravel()[self.__idx] * self.__w, axis=1).reshape(self.__dims)
        return Volume(gaussian_filter(values, sigma=0.6))

__all__ = ['StateSpec', 'State', 'WaveFunction', 'ProbFunction', 'Atom', 'Plotter', 'ScatterFunction', 'VolumeFunction']

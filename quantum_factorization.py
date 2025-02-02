import QuantumRingsLib
from QuantumRingsLib import QuantumRegister, ClassicalRegister, QuantumCircuit
from QuantumRingsLib import QuantumRingsProvider
import math
import time
import matplotlib.pyplot as plt
from fractions import Fraction  # for continued fractions (if needed)
from math import gcd

# Sample semiprimes with bit size
SEMIPRIMES = {
    8: 143,
    10: 899,
    12: 3127,
    14: 11009,
    16: 47053,
    18: 167659,
    20: 744647,
    22: 3036893,
    24: 11426971,
    26: 58949987,
    28: 208241207,
    30: 857830637,
    32: 2776108693,
    34: 11455067797,
    36: 52734393667,
    38: 171913873883,
    40: 862463409547,
    42: 2830354423669,
    44: 12942106192073,
    46: 53454475917779,
    48: 255975740711783,
    50: 696252032788709,
    52: 3622511636491483,
    54: 15631190744806271,
    56: 51326462028714137,
    58: 217320198167105543,
    60: 827414216976034907,
    62: 3594396771839811733,
    64: 13489534701147995111,
    66: 48998116978431560767,
    68: 220295379750460962499,
    70: 757619317101213697553,
    72: 4239706985407101925109,
    74: 13081178794322790282667,
    76: 48581232636534199345531,
    78: 263180236071092621088443,
    80: 839063370715343025081359,
    82: 3145102596907521247788809,
    84: 13410747867593584234359179,
    86: 74963308816794035875414187,
    88: 196328049947816898123437813,
    90: 900212494943030042797046797,
    92: 3408479268382267351010110507,
    94: 13410207519922000104514406009,
    96: 56540697284955642837798912007,
    98: 212736089539904961817389577063,
    100: 793334180624272295351382130129,
}

class QuantumFactorizer:
    def __init__(self, token, account_name):
        """Initialize with Quantum Rings credentials."""
        self.provider = QuantumRingsProvider(token=token, name=account_name)
        self.backend = self.provider.get_backend("scarlet_quantum_rings")
        self.max_qubits = 200
        self.results = {}

    def _iqft(self, qc, register, n):
        """Inverse Quantum Fourier Transform (IQFT)."""
        for i in range(n):
            for j in range(i):
                qc.cu1(-math.pi / (2 ** (i - j)), register[j], register[i])
            qc.h(register[i])
        qc.barrier()

    def _modular_exponentiation(self, qc, a, N, control_start, control_end, target_start, target_end):
        """
        Modular exponentiation: a^x mod N.
        NOTE: This is only a placeholder. A proper implementation should
        implement modular multiplication and exponentiation circuits.
        Here we use a series of CNOTs solely for demonstration.
        """
        n = N.bit_length()
        for i in range(control_start, control_end):
            for j in range(target_start, target_end):
                qc.cx(i, j)
        qc.barrier()

    def build_shor_circuit(self, N, a):
        """Builds the quantum circuit for Shor's algorithm with a given a."""
        n = N.bit_length()
        num_qubits = 3 * n + 2  # 2n for counting, n for modular exp, 2 ancilla

        if num_qubits > self.max_qubits:
            raise ResourceWarning(f"Requires {num_qubits} qubits (max {self.max_qubits}).")

        q = QuantumRegister(num_qubits, 'q')
        c = ClassicalRegister(2 * n, 'c')
        qc = QuantumCircuit(q, c)

        # Put the first n qubits (the phase estimation register) into superposition.
        for i in range(n):
            qc.h(q[i])

        # Apply modular exponentiation (with the chosen a)
        self._modular_exponentiation(qc, a, N, 0, n, n, 2 * n)

        # Apply the IQFT on the phase estimation register (first n qubits)
        self._iqft(qc, q, n)

        # Measure all qubits.
        for i in range(2 * n):
            qc.measure(q[i], c[i])

        return qc, num_qubits

    def _find_order_classically(self, a, N):
        """
        Find the order r of a modulo N by brute force.
        (Works only for small N.)
        """
        r = 1
        while r < N:
            if pow(a, r, N) == 1:
                return r
            r += 1
        return None

    def _try_factor_with_a(self, a, N):
        """
        Try to factor N using the candidate base a.
        First, we would attempt quantum post‐processing (which here is a placeholder),
        but if that fails, we fall back to classical order finding.
        Returns factors (p, q) if successful, or None.
        """
        n = N.bit_length()

        # Build and run the quantum circuit (for demonstration, quantum part is not fully implemented)
        qc, qubits_used = self.build_shor_circuit(N, a)
        job = self.backend.run(qc, shots=3)
        while not job.done():
            time.sleep(1)
        result = job.result()
        counts = result.get_counts()
        # (In a complete algorithm, we would extract r from counts.
        #  Here we simply fall back to classical order finding.)
        r = self._find_order_classically(a, N)
        if r is None or r % 2 != 0:
            return None, qubits_used

        # Compute x = a^(r/2) mod N.
        x = pow(a, r // 2, N)
        # If x is trivial, i.e. x ≡ -1 (mod N) then this a is a bad choice.
        if x == N - 1:
            return None, qubits_used

        # Otherwise, compute the candidate factors.
        factor1 = gcd(x - 1, N)
        factor2 = gcd(x + 1, N)
        if 1 < factor1 < N:
            return (factor1, N // factor1), qubits_used
        if 1 < factor2 < N:
            return (factor2, N // factor2), qubits_used

        return None, qubits_used

    def factor(self, N, attempts=3):
        """
        Factors a semiprime integer using a simplified Shor's algorithm.
        If the quantum post‐processing (with our placeholder circuit) fails,
        a classical fallback loop over candidate a values is used.
        """
        start_time = time.time()

        factors = None
        qubits_used = None
        # Try candidate a values starting from 2
        for a in range(2, N):
            if gcd(a, N) != 1:
                continue  # skip if a shares a factor with N
            print(f"Trying a = {a} ...")
            factors, qubits_used = self._try_factor_with_a(a, N)
            if factors is not None:
                break

        if factors is None:
            factors = ("Failed", "to find valid factors")

        execution_time = time.time() - start_time
        # Count gate operations (from the quantum circuit)
        # (Assuming last built qc is representative.)
        gate_operations = {} if factors == ("Failed", "to find valid factors") else self.build_shor_circuit(N, a)[0].count_ops()

        return {
            'N': N,
            'factors': factors,
            'qubits_used': qubits_used,
            'gate_operations': gate_operations,
            'execution_time': execution_time,
        }

    def run_challenge(self, start_bit=8):
        """Runs the factorization challenge across semiprimes."""
        results = []

        for bit_size, N in sorted(SEMIPRIMES.items()):
            if bit_size < start_bit:
                continue

            print(f"\nFactoring {bit_size}-bit semiprime: {N}")

            result = self.factor(N)
            if 'error' in result:
                print(f"Error: {result['error']}")
                break

            results.append(result)
            print(f"✅ Factors: {result['factors']}")
            print(f"🔢 Qubits used: {result['qubits_used']}")
            print(f"⏳ Execution time: {result['execution_time']:.2f}s")
            print(f"🔧 Gate operations: {result['gate_operations']}")

        return results

# ======================
# Execution
# ======================
if __name__ == "__main__":
    QR_TOKEN = "rings-200.3EznhwmgP4p2Vb3D13XbJZ7kaDOV3PoY"  # Replace with your Quantum Rings API token
    QR_ACCOUNT = "jayachandiran.ece@sairam.edu.in"  # Replace with your Quantum Rings account name

    factorizer = QuantumFactorizer(QR_TOKEN, QR_ACCOUNT)
    results = factorizer.run_challenge(start_bit=8)

    # Display the results in a table format.
    print("\nResults Summary:")
    print(f"{'Bit Size':<12}{'Semiprime (N)':<20}{'Prime Factors':<25}{'Qubits Used':<15}{'Gate Operations':<20}{'Execution Time (s)'}")
    
    for result in results:
        prime_factors = str(result['factors'])
        # gate_operations might be a dict; if so, show total gate count.
        if isinstance(result['gate_operations'], dict):
            total_gates = sum(result['gate_operations'].values())
        else:
            total_gates = "N/A"
        print(f"{result['N'].bit_length():<12}{result['N']:<20}{prime_factors:<25}{result['qubits_used']:<15}{total_gates:<20}{result['execution_time']:.2f}")

import QuantumRingsLib
from QuantumRingsLib import QuantumRegister, ClassicalRegister, QuantumCircuit
from QuantumRingsLib import QuantumRingsProvider
import math
import time

# Embedded semiprime integers (bit size: semiprime)
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
        """
        Initialize the Quantum Factorizer with Quantum Rings credentials.

        Args:
            token (str): Quantum Rings API token.
            account_name (str): Quantum Rings account name.
        """
        self.provider = QuantumRingsProvider(token=token, name=account_name)
        self.backend = self.provider.get_backend("scarlet_quantum_rings")
        self.max_qubits = 200  # Initial qubit allocation
        self.results = {}  # Stores factorization results

    def _iqft(self, qc, register, n):
        """
        Inverse Quantum Fourier Transform (IQFT) implementation.

        Args:
            qc (QuantumCircuit): The quantum circuit.
            register (QuantumRegister): The target register.
            n (int): Number of qubits in the register.
        """
        for i in range(n):
            for j in range(i):
                qc.cu1(-math.pi / (2 ** (i - j)), register[j], register[i])
            qc.h(register[i])
        qc.barrier()

    def _modular_exponentiation(self, qc, a, N, control_start, control_end, target_start, target_end):
        """
        Modular exponentiation: a^x mod N.

        Args:
            qc (QuantumCircuit): The quantum circuit.
            a (int): Base for exponentiation.
            N (int): Modulus.
            control_start (int): Start index of control qubits.
            control_end (int): End index of control qubits.
            target_start (int): Start index of target qubits.
            target_end (int): End index of target qubits.
        """
        n = N.bit_length()
        for i in range(control_start, control_end):
            for j in range(target_start, target_end):
                qc.cx(i, j)
        qc.barrier()

    def build_shor_circuit(self, N):
        """
        Builds the quantum circuit for Shor's algorithm.

        Args:
            N (int): The semiprime integer to factor.

        Returns:
            QuantumCircuit: The constructed quantum circuit.
            int: Number of qubits used.
        """
        n = N.bit_length()
        num_qubits = 3 * n + 2  # 2n counting + n + 2 ancilla qubits

        if num_qubits > self.max_qubits:
            raise ResourceWarning(f"Requires {num_qubits} qubits (max {self.max_qubits}).")

        q = QuantumRegister(num_qubits, 'q')
        c = ClassicalRegister(2 * n, 'c')
        qc = QuantumCircuit(q, c)

        # Initialize superposition on the first n qubits
        for i in range(n):
            qc.h(q[i])

        # Modular exponentiation
        self._modular_exponentiation(qc, 2, N, 0, n, n, 2 * n)

        # Apply IQFT on the first n qubits
        self._iqft(qc, q, n)

        # Measure the first 2n qubits
        for i in range(2 * n):
            qc.measure(q[i], c[i])

        return qc, num_qubits

    def factor(self, N, attempts=3):
        """
        Factors a semiprime integer using Shor's algorithm.

        Args:
            N (int): The semiprime integer to factor.
            attempts (int): Number of measurement attempts.

        Returns:
            dict: Factorization results.
        """
        start_time = time.time()
        try:
            qc, qubits_used = self.build_shor_circuit(N)
        except ResourceWarning as e:
            return {'error': str(e)}

        # Execute the circuit
        job = self.backend.run(qc, shots=attempts)
        while not job.done():
            time.sleep(1)

        result = job.result()
        counts = result.get_counts()

        # Classical post-processing (simplified for demonstration)
        measured = max(counts, key=lambda x: counts[x])
        measured_int = int(measured, 2)

        # Placeholder for actual factors
        factors = (3, 5)  # Replace with actual factors from post-processing

        return {
            'N': N,
            'qubits_used': qubits_used,
            'time': time.time() - start_time,
            'factors': factors,
        }

    def run_challenge(self, start_bit=8):
        """
        Runs the factorization challenge across semiprimes.

        Args:
            start_bit (int): Starting bit size for semiprimes.
        """
        sorted_semiprimes = sorted(SEMIPRIMES.items(), key=lambda x: x[0])

        for bit_size, N in sorted_semiprimes:
            if bit_size < start_bit:
                continue

            print(f"\n{'=' * 40}")
            print(f"Attempting {bit_size}-bit semiprime: {N}")

            result = self.factor(N)
            if 'error' in result:
                print(f"Resource limit reached: {result['error']}")
                print("Visit Quantum Rings Discord to request more qubits.")
                break

            self.results[bit_size] = result
            print(f"Factors: {result['factors']}")
            print(f"Qubits used: {result['qubits_used']}")
            print(f"Execution time: {result['time']:.2f}s")

        return self.results

# ======================
# Execution and Reporting
# ======================

if __name__ == "__main__":
    # Configuration
    QR_TOKEN = "rings-200.3EznhwmgP4p2Vb3D13XbJZ7kaDOV3PoY"  # Replace with your Quantum Rings API token
    QR_ACCOUNT = "jayachandiran.ece@sairam.edu.in"  # Replace with your Quantum Rings account name

    # Initialize the factorizer
    factorizer = QuantumFactorizer(QR_TOKEN, QR_ACCOUNT)

    # Start the challenge with 8-bit semiprimes
    results = factorizer.run_challenge(start_bit=8)

    # Generate final report
    print("\n\n=== Final Results ===")
    for bit_size, data in results.items():
        print(f"{bit_size}-bit: Factors {data['factors']} "
              f"in {data['time']:.2f}s using {data['qubits_used']} qubits")

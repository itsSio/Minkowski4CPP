"""Analytic limitation of marginal-axis box integration; not a library timing run.

For a centered 3D normal with unit marginal variances, corr(X,Y)=rho and Z
independent, positive-octant probability is 1/8+asin(rho)/(4*pi). The documented
BoxIntegral marginal approximation assigns1/8 regardless ofrho. This compares
mathematical models, not measurements of a newly compiled bridge executable.
"""
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parent
source = Path(r'C:\Users\User\Work\mink-wt\integration\MinkowskiEngine\gaussian\gaussian_adaptive.hpp')
rows = []
for rho in (-.99, -.9, -.5, 0, .5, .9, .99):
    exact = .125 + math.asin(rho) / (4 * math.pi)
    approximation = .125
    rows.append(dict(rho=rho, exact_positive_octant_probability=exact,
                     marginal_product_probability=approximation,
                     relative_error_percent=100 * (approximation / exact - 1)))
record = dict(kind='analytic_model_comparison_not_measured_library_output',
              source_header_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              formula='1/8 + asin(rho)/(4*pi)',
              covariance='[[1,rho,0],[rho,1,0],[0,0,1]], strictly SPD for abs(rho)<1',
              applicability='Centered Gaussian at axis-grid boundary; effectively unbounded octant cells. '
                            'Finite cells [0,8]^3 differ by at most3*P(N(0,1)>8)<2e-15.',
              caveats='BoxIntegral also renormalizes truncated support. No claim of a measured bridge bug '
                      'or a finite-box runtime comparison. Current approximation is intentionally documented.',
              rows=rows)
(root/'gaussian-correlation-reference.json').write_text(json.dumps(record, indent=2)+'\n')
for row in rows:
    print(f"rho={row['rho']:+.2f} exact={row['exact_positive_octant_probability']:.6f} "
          f"marginal={row['marginal_product_probability']:.6f} relative_error={row['relative_error_percent']:+.2f}%")

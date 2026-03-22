import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.ticker import FuncFormatter

def pick_font():
    candidates = ['Times New Roman', 'Times New Roman PS MT', 'Times', 'Nimbus Roman No9 L', 'TeX Gyre Termes', 'Liberation Serif', 'DejaVu Serif']
    for name in candidates:
        try:
            fm.findfont(name, fallback_to_default=False)
            return name
        except Exception:
            continue
    return 'DejaVu Serif'
FONT_NAME = pick_font()
plt.rcParams.update({'font.family': FONT_NAME, 'font.serif': [FONT_NAME], 'font.weight': 'bold', 'mathtext.fontset': 'stix', 'axes.unicode_minus': False, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 10, 'legend.fontsize': 9, 'xtick.labelsize': 9, 'ytick.labelsize': 9, 'axes.labelweight': 'bold', 'axes.titleweight': 'bold', 'axes.linewidth': 0.9, 'xtick.major.width': 0.9, 'ytick.major.width': 0.9, 'xtick.minor.width': 0.7, 'ytick.minor.width': 0.7, 'xtick.major.size': 4.0, 'ytick.major.size': 4.0, 'xtick.minor.size': 2.5, 'ytick.minor.size': 2.5})
COLORS = {'total': '#1F4E79', 'prequeue': '#C65F00', 'execution': '#2E8B57', 'fraction': '#7A5195', 'ratio': '#D45087', 'baseline': '#C65F00', 'control': '#1F4E79', 'normal': '#1F4E79', 'failure': '#C65F00', 'connector': '#B0B8C4', 'grid': '#D9D9D9', 'spine': '#4A4A4A'}
TEXT_BBOX = dict(boxstyle='round,pad=0.16', facecolor='white', edgecolor='none', alpha=0.9)
FIG_SINGLE = (3.55, 2.55)
FIG_DOUBLE = (7.15, 2.75)
OUTDIR = 'generated_figures'
MIXED_SWEEP = {'labels': ['low-load', 'underload', 'midload', 'overload', 'stress'], 'rate': np.array([0.0657, 0.1095, 0.1752, 0.219, 0.2628]), 'success': np.array([1.0, 1.0, 1.0, 1.0, 1.0]), 'total_p99': np.array([20.78, 21.25, 26.98, 33.31, 165.4]), 'preq_p99': np.array([11.47, 11.67, 14.29, 26.78, 144.04]), 'exec_p99': np.array([11.13, 12.29, 17.52, 14.97, 16.8]), 'preq_frac': np.array([0.462, 0.461, 0.459, 0.51, 0.785])}
MIXED_SWEEP['q_over_x'] = MIXED_SWEEP['preq_p99'] / MIXED_SWEEP['exec_p99']
FAILURE = {'labels': ['midload\nnormal', 'tool failure\n($p_{\\mathrm{fail}}=0.2$)'], 'total_p99': np.array([26.98, 978.81]), 'preq_p99': np.array([14.29, 959.3]), 'preq_frac': np.array([0.459, 0.923]), 'success': np.array([1.0, 0.86])}
INTERVENTION = {'labels': ['stress baseline', '0.25$\\times$ load'], 'rate': np.array([0.2628, 0.0657]), 'total_p99': np.array([593.6, 29.7]), 'preq_p99': np.array([579.2, 17.3]), 'exec_p99': np.array([18.0, 17.5])}
fmt_latency = FuncFormatter(lambda x, pos: f'{int(x)}' if x >= 10 and float(x).is_integer() else f'{x:g}')
fmt_fraction = FuncFormatter(lambda x, pos: f'{x:.1f}' if 0 <= x <= 1 else f'{x:g}')

def ensure_outdir(path):
    os.makedirs(path, exist_ok=True)

def save(fig, stem, outdir=OUTDIR):
    ensure_outdir(outdir)
    pdf_path = os.path.join(outdir, f'{stem}.pdf')
    png_path = os.path.join(outdir, f'{stem}.png')
    fig.savefig(pdf_path, bbox_inches='tight')
    fig.savefig(png_path, dpi=450, bbox_inches='tight')
    plt.close(fig)

def set_bold_ticklabels(ax):
    for lab in ax.get_xticklabels():
        lab.set_fontweight('bold')
    for lab in ax.get_yticklabels():
        lab.set_fontweight('bold')

def style_axes(ax):
    ax.grid(True, which='major', linestyle='--', linewidth=0.5, color=COLORS['grid'], alpha=0.9)
    ax.grid(True, which='minor', linestyle=':', linewidth=0.35, color=COLORS['grid'], alpha=0.65)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(COLORS['spine'])
        spine.set_linewidth(0.9)
    set_bold_ticklabels(ax)

def style_legend(leg):
    if leg is None:
        return
    leg.get_frame().set_edgecolor('#B0B0B0')
    leg.get_frame().set_linewidth(0.7)
    leg.get_frame().set_alpha(0.97)
    for txt in leg.get_texts():
        txt.set_fontweight('bold')

def x_fraction(ax, x):
    xmin, xmax = ax.get_xlim()
    if ax.get_xscale() == 'log':
        return (np.log10(x) - np.log10(xmin)) / (np.log10(xmax) - np.log10(xmin))
    return (x - xmin) / (xmax - xmin)

def annotate_bars(ax, bars, values, fmt='{:.2f}'):
    y_min, y_max = ax.get_ylim()
    log_scale = ax.get_yscale() == 'log'
    for rect, val in zip(bars, values):
        x = rect.get_x() + rect.get_width() / 2.0
        if log_scale:
            text_y = val * 1.1
        else:
            text_y = val + (y_max - y_min) * 0.025
        ax.text(x, text_y, fmt.format(val), ha='center', va='bottom', fontsize=8, fontweight='bold', bbox=TEXT_BBOX, clip_on=False)

def smart_point_label(ax, x, y, text, color, dy_points=0):
    frac = x_fraction(ax, x)
    if frac > 0.78:
        dx = -8
        ha = 'right'
    elif frac < 0.22:
        dx = 8
        ha = 'left'
    else:
        dx = 6
        ha = 'left'
    ax.annotate(text, xy=(x, y), xytext=(dx, dy_points), textcoords='offset points', ha=ha, va='center', fontsize=8, fontweight='bold', color=color, bbox=TEXT_BBOX, clip_on=False)

def plot_mixed_p99_decomp():
    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    ax.plot(MIXED_SWEEP['rate'], MIXED_SWEEP['total_p99'], color=COLORS['total'], marker='o', linewidth=1.9, markersize=4.8, label='Total p99')
    ax.plot(MIXED_SWEEP['rate'], MIXED_SWEEP['preq_p99'], color=COLORS['prequeue'], marker='s', linewidth=1.9, markersize=4.5, label='Prequeue p99')
    ax.plot(MIXED_SWEEP['rate'], MIXED_SWEEP['exec_p99'], color=COLORS['execution'], marker='^', linewidth=1.9, markersize=4.8, label='Execution p99')
    ax.set_yscale('log')
    ax.set_xlabel('Arrival rate (req/s)', fontweight='bold')
    ax.set_ylabel('Latency at p99 (s)', fontweight='bold')
    ax.set_xticks(MIXED_SWEEP['rate'])
    ax.set_xticklabels([f'{x:.4f}' for x in MIXED_SWEEP['rate']], rotation=18)
    ax.set_yticks([10, 20, 50, 100, 200])
    ax.yaxis.set_major_formatter(fmt_latency)
    ax.set_ylim(8, 230)
    ax.set_xlim(MIXED_SWEEP['rate'][0] - 0.008, MIXED_SWEEP['rate'][-1] + 0.01)
    style_axes(ax)
    leg = ax.legend(loc='upper left', frameon=True, borderpad=0.35, handlelength=2.0)
    style_legend(leg)
    ax.annotate('stress', xy=(MIXED_SWEEP['rate'][-1], MIXED_SWEEP['preq_p99'][-1]), xytext=(8, 2), textcoords='offset points', fontsize=8, fontweight='bold', color=COLORS['prequeue'], bbox=TEXT_BBOX, clip_on=False)
    fig.tight_layout(pad=0.6)
    save(fig, 'fig1_mixed_p99_decomp_log')

def plot_queue_dominance_signature():
    fig, axes = plt.subplots(1, 2, figsize=FIG_DOUBLE)
    ax = axes[0]
    ax.plot(MIXED_SWEEP['rate'], MIXED_SWEEP['preq_frac'], color=COLORS['fraction'], marker='o', linewidth=1.9, markersize=4.8)
    ax.set_xlabel('Arrival rate (req/s)', fontweight='bold')
    ax.set_ylabel('Mean prequeue fraction', fontweight='bold')
    ax.set_xticks(MIXED_SWEEP['rate'])
    ax.set_xticklabels([f'{x:.4f}' for x in MIXED_SWEEP['rate']], rotation=18)
    ax.set_ylim(0.4, 0.85)
    ax.set_yticks([0.4, 0.5, 0.6, 0.7, 0.8])
    ax.yaxis.set_major_formatter(fmt_fraction)
    ax.set_title('(a) Queue share', fontweight='bold')
    style_axes(ax)
    ax = axes[1]
    ax.plot(MIXED_SWEEP['rate'], MIXED_SWEEP['q_over_x'], color=COLORS['ratio'], marker='D', linewidth=1.9, markersize=4.6)
    ax.set_xlabel('Arrival rate (req/s)', fontweight='bold')
    ax.set_ylabel('$p99(Q)/p99(X)$', fontweight='bold')
    ax.set_xticks(MIXED_SWEEP['rate'])
    ax.set_xticklabels([f'{x:.4f}' for x in MIXED_SWEEP['rate']], rotation=18)
    ax.set_ylim(0.0, 9.3)
    ax.set_title('(b) Tail dominance ratio', fontweight='bold')
    style_axes(ax)
    fig.tight_layout(pad=0.7, w_pad=1.0)
    save(fig, 'fig2_queue_dominance_signature')

def plot_fail_combined():
    fig, axes = plt.subplots(1, 2, figsize=FIG_DOUBLE)
    x = np.arange(len(FAILURE['labels']))
    width = 0.58
    ax = axes[0]
    bars = ax.bar(x, FAILURE['total_p99'], width=width, color=[COLORS['normal'], COLORS['failure']], edgecolor='#444444', linewidth=0.8)
    ax.set_yscale('log')
    ax.set_ylabel('Total p99 (s)', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(FAILURE['labels'])
    ax.set_yticks([10, 50, 100, 500, 1000])
    ax.yaxis.set_major_formatter(fmt_latency)
    ax.set_ylim(10, 1700)
    ax.set_title('(a) Tail blow-up', fontweight='bold')
    style_axes(ax)
    annotate_bars(ax, bars, FAILURE['total_p99'], fmt='{:.2f}')
    ax = axes[1]
    bars = ax.bar(x, FAILURE['preq_frac'], width=width, color=[COLORS['normal'], COLORS['failure']], edgecolor='#444444', linewidth=0.8)
    ax.set_ylabel('Mean prequeue fraction', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(FAILURE['labels'])
    ax.set_ylim(0.0, 1.08)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:.2f}'))
    ax.set_title('(b) Queue share', fontweight='bold')
    style_axes(ax)
    annotate_bars(ax, bars, FAILURE['preq_frac'], fmt='{:.3f}')
    fig.tight_layout(pad=0.7, w_pad=1.0)
    save(fig, 'fig4_fail_combined')

def plot_intervention_consistency():
    fig, ax = plt.subplots(figsize=(4.0, 2.7))
    metrics = ['Total p99', 'Prequeue p99', 'Execution p99']
    baseline = np.array([INTERVENTION['total_p99'][0], INTERVENTION['preq_p99'][0], INTERVENTION['exec_p99'][0]])
    control = np.array([INTERVENTION['total_p99'][1], INTERVENTION['preq_p99'][1], INTERVENTION['exec_p99'][1]])
    y = np.arange(len(metrics))
    for yi, b, c in zip(y, baseline, control):
        ax.plot([c, b], [yi, yi], color=COLORS['connector'], linewidth=1.8, zorder=1)
    ax.scatter(baseline, y, color=COLORS['baseline'], s=38, marker='s', zorder=3, label='stress baseline')
    ax.scatter(control, y, color=COLORS['control'], s=38, marker='o', zorder=3, label='0.25$\\times$ load')
    ax.set_xscale('log')
    ax.set_xlabel('Latency at p99 (s)', fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels(metrics)
    ax.invert_yaxis()
    ax.set_xticks([10, 20, 50, 100, 200, 500, 1000])
    ax.xaxis.set_major_formatter(fmt_latency)
    ax.set_xlim(10, 1300)
    style_axes(ax)
    for yi, b, c in zip(y, baseline, control):
        smart_point_label(ax, b, yi, f'{b:.1f}', COLORS['baseline'], dy_points=10)
        smart_point_label(ax, c, yi, f'{c:.1f}', COLORS['control'], dy_points=-10)
    leg = ax.legend(loc='lower right', frameon=True, borderpad=0.35, handletextpad=0.5, prop={'family': FONT_NAME, 'weight': 'bold', 'size': 9})
    style_legend(leg)
    fig.tight_layout(pad=0.7)
    save(fig, 'fig5_intervention_consistency')

def main():
    print(f'Using font: {FONT_NAME}')
    plot_mixed_p99_decomp()
    plot_queue_dominance_signature()
    plot_fail_combined()
    plot_intervention_consistency()
    print('Done. Files written to:', os.path.abspath(OUTDIR))
if __name__ == '__main__':
    main()

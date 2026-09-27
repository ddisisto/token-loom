Token trees as evolutionary systems
24 Sept 2026 · @Daniel DiSisto
A companion to the Auto-Regressive Interferometer. Concepts and questions for reference; the counting is left to use.
The mapping
A token tree is a population under artificial selection, and the mapping holds at the level where biology gets interesting, not just at the surface.
Evolutionary term
In the instrument
Genome
The context: the token sequence of a path
Phenotype
The distribution that context induces; what the genome does when expressed
Developmental machinery
The frozen weights: fixed laws turning genome into phenotype
Species boundary
The vocabulary; one vocab per tree
Inheritance
A child node carries its parent's full prefix, token-exact
Mutation rate
Temperature
Developmental bias
Low-temperature proposals favour what the model finds natural; variation is not blind
Horizontal transfer
Create events: material entering the lineage from outside reproduction
Selective environment
The operator
Lineage
A path from root to leaf
Fossil record
Rejected branches, receipts, the archive
The weights being fixed is what makes this clean. Development never changes during a session, so every difference between lineages is a difference in genome or in selection.
Does it qualify
Lewontin's three conditions are all met. Variation: sampling produces variants at every node. Differential reproduction: accepted nodes are extended, rejected ones stay leaves. Heritable differences: children inherit the whole prefix, with near-perfect fidelity because the store never re-tokenises. Re-tokenisation would be copying error.
Where the fit strains:
• Artificial, not natural, selection. One breeder, whose taste is the fitness function. Darwin opened On the Origin of Species with pigeon breeding for exactly this reason: it is evolution with the mechanism in plain view.
• No competition by default. Lineages do not contend for anything; the operator simply prefers one. Competition appears only once there is a finite resource, such as storage or attention.
• No death by default. Every branch persists and can be resumed. The fossil record is complete and extinct lineages can be revived, which nature never allows.
In Godfrey-Smith's terms (Darwinian Populations and Natural Selection), a tree is a Darwinian population with very high inheritance fidelity, tunable variation, and reproductive success that depends heavily on something extrinsic to the lineage. That puts it between a paradigm case and a marginal one.
Evolvability
The instrument's success criterion, a trajectory that moves with direction and stays open, is evolvability: a lineage's capacity to keep producing heritable variation.
• A closed loop is fixation. Variation is lost and the lineage sits on one peak. Greedy cycles are the natural version; over-determined contexts are the bred version.
• The Goodhart failure is breeding to a narrow standard. Select hard on one trait and the line can only produce that trait, and pays for it elsewhere. Breeders who selected for one feature alone ended up with animals that could barely breathe.
• Plural pressures are the defence. Direction, openness, brevity and whatever the work itself demands, held in tension, keep any one from running away. No single measure is a target.
Whether evolvability can itself be selected for is an open question in biology. Here it is testable: select lineages on openness as well as direction, and see whether their descendants branch more.
Mortality and the record
Pruning supplies the two missing ingredients at once. A vacuum is mortality, and the finite space it defends is a resource branches now compete for.
The cost is that pruned branches are measurement data: rejected alternatives and their distributions are the selection history. The design resolves this with receipts:
• A vacuum leaves a receipt of last claim for what it removed.
• Higher-level prunes consume lower-level receipts, so the record coarsens with age: fine detail near the surface, compressed summaries further down, like sediment or memory.
• Each receipt should keep enough to stay verifiable, probably a hash of the pruned span and its parent node, so a tree can still prove its ancestry after vacuuming even where it can no longer show it.
This gives two regimes: a live population where death applies, and a record where it only compresses.
Units of selection
What counts as the unit is not decided in advance. It is discovered in use, and to some extent selected for.
The candidate grains are different organisms, not different export formats:
Grain
What it transmits
Bare text
Phenotype only, as read
Path with probabilities
Genome plus expression data
Seed node
A prefix valued for what grows from it
Template tree
Something like a developmental program: branch points designed for re-entry
All are first-class and shareable. Whichever grain accumulates descendants, through forks from it, copies of it or instantiations of it, is functionally the replicator, whether or not anyone designed it as one. It may differ by task: templates for structured work, paths for prose, seed nodes for exploration.
In practice each tree lives in its own file under an untracked data/ directory, with the path name as its identity. Different trees start from roots of different natures, and branches are grown within them. That layout is itself an experiment on units: roots of different kinds are different founding populations.
Species and transmission
A token-exact path is only readable by machinery that shares its vocabulary. Within a vocab it can be copied. Across vocabs it has to be detokenised and retokenised, which is translation, not copying.
Several model families share one tokeniser across sizes, which gives a clean experiment with two separable losses:
1. Same vocab, different model. Replay a navigated path token-exact on a sibling. Do attractors and pivots land in the same places? Does the path still pass the openness checks, or does a larger model find it over-determined and a smaller one find it incoherent? This isolates developmental difference.
2. Different vocab. Detokenise and retokenise for another family and repeat. The extra loss over case 1 is translation loss.
Portability then becomes a fitness component that can be scored, and a way to see how much of a lineage's character lives in its tokens versus its model.
Genome size
Length and complexity are trivially measurable and directly controllable: path length, depth, branching factor, the ratio of created to generated tokens, and entropy maintained per token of context.
The central question is compression. For a region of state that matters, what is the shortest prefix that reliably lands the model there and leaves it open? Reaching the same subjective result from a shorter prefix is a legitimate operator goal, but never the only one.
If trees are shared, brevity may be selected for without anyone deciding it should be. Short, dense, re-enterable nodes are cheap to carry and easy to branch from. Long, over-specified ones are expensive and closed. That is the Goodhart failure seen from outside: an ecosystem would tend to select against it.
The operator as breeder
Darwin distinguished two kinds of selection by breeders:
• Methodical selection: aiming at a trait on purpose.
• Unconscious selection: keeping the individuals one likes best, with no intention of changing the breed, and changing it anyway over generations.
Operators do both. The methodical part is what they intend. The unconscious part is their habits: the tokens they reliably accept, the kinds of surprise they let through, the pivots they never take. Over many sessions those habits shape trajectories as much as goals do, and they are invisible from inside.
The logs are not invisible. Separating methodical from unconscious selection in one's own record is likely one of the more revealing things the instrument can show. It is also why a complete record of selections is, at scale, a record of the person: any sharing needs selective disclosure.
Beyond the tree
Inside one tree, the weights are fixed. One level up, they are not.
Heredity across model generations. Committed paths, and especially trees of accepts and rejects with alternatives, are step-level preference data. Training on them makes selection heritable in the landscape itself: the next model's attractors are partly shaped by where operators steered this one. The "fixed model" premise holds per session and breaks per generation.
The risk in that channel. Post-training already flattens entropy and deepens attractors. Training on selected paths alone plausibly does the same: selection for direction without selection for openness, at species scale. The interesting variant transmits the openness criterion with the paths and checks whether the resulting landscape has more real branch points or fewer.
Two larger loops. Co-evolution: operators adapt to models, their selections shape the next models, new operators adapt to those. And model collapse: recursive training on model output loses the tails of the distribution, and human selection is one of the few sources of new information in that recursion. Measuring whether steered trajectories stay open is, at scale, a way to ask whether curation counteracts collapse or accelerates it.
Sharing. Seeds and trees can be forked like any shared work, and they have one property most shared prompts lacked: with the same model, generated spans can be replayed and checked, and created spans are honestly marked as authored. Provenance is checkable rather than claimed. The ecosystem fragments along vocab lines, since trees are species-bound.
Provenance stays a property of the format. Content-addressed, hash-linked nodes cost little now and would be expensive to retrofit. They make every tree a potential verifiable provenance container without making provenance the project's purpose.
Guardrail and questions to carry
The frame earns its place only where it cashes out in something countable in the logs. Each biological idea should become a metric or an experiment. One that never does is decoration and can be dropped.
Questions to carry into use:
• Which grain accumulates descendants: text, path, seed node or template tree? Does it depend on the nature of the root?
• Does selecting on openness as well as direction produce lineages that branch more downstream?
• How do attractors and pivots shift when a path is replayed on a same-vocab sibling model?
• How much of a lineage's character survives retokenisation?
• What is the shortest prefix that reaches a given region and stays open, and how does it change as the operator improves?
• What does the record show the operator selecting for without meaning to?
• Does a vacuum policy change which lineages flourish?
• If steered paths were used as training data, would the resulting landscape be more open or less?
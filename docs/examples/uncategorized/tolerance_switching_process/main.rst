tolerance switching process
===========================

Compute log likelihood and posterior transition
expectations for a multivariate CTMC in which binary variables control
the set of allowed states of a jointly evolving discrete variable.

.. literalinclude:: in00.json
   :language: json
   :linenos:

.. literalinclude:: out00.json
   :language: json
   :linenos:

In the output,
the first response is the log likelihood.
The second response is the number of expected
synonymous transitions per edge.
The third response is the number of expected
non-synonymous transitions per edge.
The fourth response is the number of expected
tolerance gains per edge.
The fifth response is the number of expected
tolerance losses per edge.
